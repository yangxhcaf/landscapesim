import csv
import json
import os
import re
from shutil import copyfile
from time import sleep, time
from uuid import uuid4

from celery.task import task
from django.conf import settings

from landscapesim.common.config import CONFIG_IMPORTS, VALUE_IMPORTS
from landscapesim.common.consoles import STSimConsole
from landscapesim.common.geojson import rasterize_geojson
from landscapesim.common.query import ssim_query
from landscapesim.common.services import ServiceGenerator
from landscapesim.common.utils import get_random_csv
from landscapesim.importers import ScenarioImporter, ReportImporter
from landscapesim.models import Library, Scenario, TransitionGroup, RunScenarioModel
from landscapesim.serializers import imports

EXE = getattr(settings, 'STSIM_EXE_PATH')
SCENARIO_SCAN_RATE = 2
DATASET_DOWNLOAD_DIR = getattr(settings, 'DATASET_DOWNLOAD_DIR')
STSIM_MULTIPLIER_DIR = getattr(settings, 'STSIM_MULTIPLIER_DIR')


class ModelBootstrapper:
    """
    A class for performing model startup and synchronization between LandscapeSim and SyncroSim.

    This is the entry point for importing a model configuration from LandscapeSim back into SyncroSim. At this point,
    all validation has occurred for the model configuration, and so inputs from the validated configuration can safely
    be imported into SyncroSim. Specifics for how that import is done are handled both by this class and the
    Celery tasks that are executed using this class.
    """

    def __init__(self, scenario_id, library, config, console: STSimConsole, job):
        self.scenario_id = scenario_id
        self.config = config
        self.console = console
        self.job = job
        self.library = library

    @property
    def temp_file(self):
        return get_random_csv(self.library.tmp_file)

    def filter_and_create_initial_conditions_spatial(self):
        pass  # Todo - create spatially-explicit initial conditions from special arguments (e.g. Landfire)

    def filter_and_create_transition_spatial_multipliers(self):
        """ Takes a configuration, filters out geojson-specific data, and returns a valid configuration for import. """

        scenario = self.library.projects.filter(scenarios__sid=self.scenario_id).first().scenarios.get(
            sid=self.scenario_id
        )
        if scenario.run_control.is_spatial:

            # unique identifier for these spatial multipliers
            uuid = str(uuid4())

            # For each transition spatial multipler, create spatial multiplier files where needed
            for tsm in self.config['transition_spatial_multipliers']:
                tg = TransitionGroup.objects.get(id=tsm['transition_group']).name
                it = int(tsm['iteration']) if tsm['iteration'] is not None else 'all'
                ts = int(tsm['timestep']) if tsm['timestep'] is not None else 'all'
                tsm_file_name = "{uuid}_{tg}_{it}_{ts}.tif".format(uuid=uuid, tg=tg, it=it, ts=ts)
                tsm['transition_multiplier_file_name'] = tsm_file_name
                try:
                    geojson = tsm.pop('geojson')  # always remove the geojson entry
                    try:
                        template_path = os.path.join(
                            scenario.input_directory, scenario.initial_conditions_spatial_settings.stratum_file_name
                        )
                        out_path = os.path.join(STSIM_MULTIPLIER_DIR, tsm_file_name)
                        rasterize_geojson(geojson, template_path=template_path, out_path=out_path, save_geojson=True)
                    except:
                        raise IOError("Error rasterizing geojson.")
                except KeyError:
                    print('{tg} multiplier did not have geojson attached, skipping...'.format(tg=tg))
        else:
            # We don't want to import any spatial multipliers, so filter out of configuration
            self.config['transition_spatial_multipliers'] = []

    def validate_configuration(self):
        """ Main model run validation and transformation of data into importable info into SyncroSim. """

        # Handle special filtering and file creation prior to model runs
        self.filter_and_create_initial_conditions_spatial()
        self.filter_and_create_transition_spatial_multipliers()

        # Now validate and deserialize into SyncroSim formats.
        for key, deserializer in imports.CONFIG_INPUTS + imports.VALUE_INPUTS:
            self.config[key] = deserializer(self.config[key]).validated_data

    def setup_transition_spatial_multipliers(self):
        """
        If there are transition spatial multipliers, move them to the appropriate scenario location on disk.
        """
        parent = self.job.parent_scenario
        for tsm in self.config['transition_spatial_multipliers']:
            filename = tsm['MultiplierFileName']
            src = os.path.join(STSIM_MULTIPLIER_DIR, filename)
            dst = os.path.join(parent.multiplier_directory, filename)
            if not os.path.exists(parent.multiplier_directory):
                os.makedirs(parent.multiplier_directory)
            copyfile(src, dst)
            os.remove(src)      # Once the file is copied, we can cleanup the transition multipliers

    def import_configuration(self):
        """ Imports validated run configuration into csv formatted sheets for import. """

        print('Importing configuration for Scenario {}'.format(self.scenario_id))
        for pair in CONFIG_IMPORTS + VALUE_IMPORTS:
            key = pair[0]
            sheet_name = pair[1]
            field_map = pair[2]
            fieldnames = [x[1] for x in field_map]
            importable_data = self.config[key]
            filename = self.temp_file
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                if pair in CONFIG_IMPORTS:
                    writer.writerow(importable_data)
                else:
                    for row in importable_data:
                        writer.writerow(row)
            print('Importing data for {}'.format(sheet_name))
            self.console.import_sheet(sheet_name, filename, sid=self.scenario_id, cleanup=True)
        print('Successfully imported run configuration for scenario {}'.format(self.scenario_id))

    def execute_ssim_queries(self):
        """
        Execute SQL Queries to apply directly to a SyncroSim file.
        It is sometimes necessary to delete or configure aspects of the SyncroSim database to ensure that certain
        conditions are met. For example, it is impossible to import an empty sheet into SyncroSim. However, to ensure
        that when we do actually want to eliminate all possible rows for a given sheet (i.e. Transition Spatial
        Multipliers), we need to preform these actions.
        """

        # Currently no support for importing an empty table.
        # However, if there are no transition multipliers, delete them from the database.
        if len(self.config.get('transition_spatial_multipliers')) == 0:
            ssim_query(
                "DELETE FROM STSim_TransitionSpatialMultiplier WHERE ScenarioID={}".format(self.scenario_id),
                self.library
            )

    def run_setup(self):
        """ Perform the LandscapeSim -> SyncroSim import. """
        print('Validating scenario configuration...')
        self.validate_configuration()
        print('Creating transition spatial_multipliers...')
        self.setup_transition_spatial_multipliers()
        print('Importing scenario configuration...')
        self.import_configuration()
        print('Finalizing import...')
        self.execute_ssim_queries()
        self.job.model_status = 'running'
        self.job.save()

    def run_model(self):
        print('Running scenario {}...'.format(self.scenario_id))
        return int(self.console.run_model(self.scenario_id))


@task
def look_for_new_scenario(run_id):
    """ Scan for the new scenario that was created. """
    run = RunScenarioModel.objects.get(id=run_id)

    # If run is not spatial, return immediately
    is_spatial = json.loads(run.inputs)['config']['run_control']['is_spatial']
    if not is_spatial:
        return

    recorded_sids = {x['sid'] for x in Scenario.objects.filter(is_result=True).values('sid')}
    spatial_directories = os.listdir(os.path.dirname(os.path.dirname(run.parent_scenario.output_directory)))
    directory_sids = {int(x.split('-')[1]) for x in spatial_directories}
    new_sids = directory_sids - recorded_sids
    if new_sids:
        sid = new_sids.pop()
        scenario, _ = Scenario.objects.get_or_create(
                    project=run.parent_scenario.project,
                    name=run.parent_scenario.name,
                    sid=sid,
                    is_result=True,
                    parent=run.parent_scenario
            )
        run.result_scenario = scenario
        run.save()
    else:
        sleep(SCENARIO_SCAN_RATE)
        look_for_new_scenario.delay(run_id)


@task(bind=True)
def run_model(self, library_name, sid):
    """
    Where all the magic happens. We perform a full import process into SyncroSim, let the model run complete, and then
    capture a snapshot of the library inputs and outputs and record them in our database. We also create all necessary
    input and output ncdjango services to provide map information.
    :param self: The celery task instance
    :param library_name: Unique name of the library containing the project.
    :param sid: The scenario id which we are running the model on. The scenario must not be a result scenario.
    """
    lib = Library.objects.get(name__iexact=library_name)
    console = STSimConsole(exe=EXE, lib_path=lib.file, orig_lib_path=lib.orig_file)
    job = RunScenarioModel.objects.get(celery_id=self.request.id)
    job.model_status = 'starting'
    job.save()

    # Configure ST-Sim configuration
    config = json.loads(job.inputs)['config']
    boot = ModelBootstrapper(sid, lib, config, console, job)
    boot.run_setup()

    # Execute model run
    try:
        look_for_new_scenario.delay(job.id)
        result_sid = boot.run_model()
    except:
        raise IOError("Error running model")

    # Create initial LandscapeSim entries
    scenario_info = console.get_scenario_attrs(result_sid)
    print('Model run complete - new scenario created: {}'.format(result_sid))
    scenario, created = Scenario.objects.get_or_create(
        project=job.parent_scenario.project,
        name=scenario_info['name'],
        sid=result_sid,
        is_result=True,
        parent=job.parent_scenario
    )

    # If running spatially, we should have caught the scenario 
    if not created:
        job.refresh_from_db()
    else:
        job.result_scenario = scenario
    job.outputs = json.dumps({'result_scenario': {'id': scenario.id, 'sid': scenario.sid}})
    job.model_status = 'processing'
    job.save()

    # Begin importing data into LandscapeSim
    importer = ScenarioImporter(console, scenario)
    importer.import_run_control()
    importer.import_output_options()

    # Create ncdjango services
    service_generator = ServiceGenerator(scenario)
    service_generator.create_output_services()

    # Create reports
    reporter = ReportImporter(console, scenario)
    reporter.create_stateclass_summary()

    # Signal that the model can now be used for viewing.
    job.model_status = 'complete'
    job.save()

    # Continue post-processing task for later usage and free the worker.
    post_process_results.delay(job.id)


@task
def post_process_results(run_id):
    run = RunScenarioModel.objects.get(id=run_id)
    scenario = run.result_scenario
    console = STSimConsole(lib_path=scenario.library.file, orig_path=scenario.library.orig_file, exe=EXE)
    ScenarioImporter(console, scenario).import_post_processed_sheets(create_input_services=False)


@task
def cleanup_temp_files(age=7200):
    cutoff = time() - age
    t_files = os.listdir(DATASET_DOWNLOAD_DIR)
    for t_file in t_files:
        if re.search('.zip$', t_file):
            path = os.path.join(DATASET_DOWNLOAD_DIR, t_file)
            if os.path.getctime(path) < cutoff:
                try:
                    os.remove(path)
                except OSError:
                    pass
        if re.search('.pdf$', t_file):
            path = os.path.join(DATASET_DOWNLOAD_DIR, t_file)
            if os.path.getctime(path) < cutoff:
                try:
                    os.remove(path)
                except OSError:
                    pass
