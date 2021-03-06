import csv
import os
from inspect import isfunction

from django.conf import settings

from landscapesim.models import Project, Scenario

DEBUG = getattr(settings, 'DEBUG')


class ImporterBase:
    """
    Base class for designing importer classes, responsible for exporting data from SyncroSim and creating
    database entries for use in the LandscapeSim API.
    """

    related_model = None

    def __init__(self, console, filter_obj=None, temp_file=None):
        """
        Constructor
        :param console: The STSimConsole to be used for importing project data with.
        :param filter_obj: The Django model instance to filter types on. For example, when importing a specific
        Project's information, filter_obj should be the Project object instance to be imported.
        :param temp_file: The path to a template CSV file to be used for importing data to.
        """
        if not isinstance(filter_obj, self.related_model):
            raise TypeError(
                "Provided filter object of type {} is not valid for this importer.".format(type(self.related_model))
            )

        self.console = console
        self.filter_obj = filter_obj
        self.temp_file = temp_file
        self.sheet_kwargs = {}
        self.project = None
        self.scenario = None
        self.import_kwargs = {}

        relationship = None
        if isinstance(filter_obj, Project):
            self.project = filter_obj
            relationship = 'project'
        elif isinstance(filter_obj, Scenario):
            self.scenario = filter_obj
            self.project = self.scenario.project
            relationship = 'scenario'

        if relationship is not None:
            self.import_kwargs[relationship] = self.filter_obj

    def _cleanup_temp_file(self):
        if not DEBUG and os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def map_row(self, row_data, sheet_map, type_map):
        """
        Map a row of data using the sheet_map and type_map to keyword arguments for creating a database entry.

        *** NOTE ***
        This method should be overridden if there are specific ways that the row data needs to be imported.
        For example, using external data sources for mapping unique identifiers with internal model identifiers
        is a good use case.

        :param row_data A dictionary of data extracted from a row of a SyncroSim sheet export.
        :param sheet_map The name mapping (see landscapesim.io.config)
        :param type_map Type casting for handling the conversions between SyncroSim and LandscapeSim.
        """
        result = {}
        for pair, type_or_filter in zip(sheet_map, type_map):

            # Skip entries in mapping that are not handled by LandscapeSim
            if type_or_filter is None:
                continue

            model_field, sheet_field = pair
            data = row_data[sheet_field]
            is_filter = not (isinstance(type_or_filter, type) or isfunction(type_or_filter))
            result[model_field] = type_or_filter.get(data, self.project) if is_filter else type_or_filter(data)
        return result

    def _extract_sheet(self, sheet_config):
        """ Extract data from the STSimConsole and import into LandscapeSim. """
        sheet_name, model, sheet_map, type_map = sheet_config
        self.console.export_sheet(sheet_name, self.temp_file, **self.sheet_kwargs)
        with open(self.temp_file, 'r') as sheet:
            reader = csv.DictReader(sheet)
            data = [r for r in reader]
            for row in data:
                instance_data = {**self.import_kwargs, **self.map_row(row, sheet_map, type_map)}
                model.objects.create(**instance_data)
        print("Imported {}".format(sheet_name))
        self._cleanup_temp_file()
