import uuid
import csv
import os
from landscapesim.models import Terminology, Stratum, SecondaryStratum, StateClass, TransitionType, \
    TransitionGroup, TransitionTypeGroup, TransitionMultiplierType, \
    RunControl, OutputOption, DeterministicTransition, Transition, InitialConditionsNonSpatial, \
    InitialConditionsNonSpatialDistribution, TransitionTarget, TransitionMultiplierValue, \
    AttributeGroup, StateAttributeType, TransitionAttributeType, TransitionSizeDistribution, \
    TransitionSizePrioritization, TransitionSpatialMultiplier, StateAttributeValue, TransitionAttributeValue, \
    TransitionAttributeTarget

M2_TO_ACRES = 0.000247105


# meters squard to acres
def cells_to_acres(numcells, res):
    return pow(res, 2) * M2_TO_ACRES * numcells


def order():
    return lambda t: t[0]


def get_random_csv(file):
    return file.replace('.csv', str(uuid.uuid4()) + '.csv')


def color_to_rgba(colorstr):
    r, g, b, a = colorstr.split(',')
    return {'r': r, 'g': g, 'b': b, 'a': a}


def process_project_definitions(console, project):

    tmp_file = get_random_csv(project.library.tmp_file)
    kwgs = {'pid': project.pid, 'overwrite': True, 'orig': True}

    # Import terminology
    console.export_sheet('STSim_Terminology', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        terms = [r for r in reader][0]
        Terminology.objects.create(
            project=project,
            amount_label=terms['AmountLabel'],
            amount_units=terms['AmountUnits'],
            state_label_x=terms['StateLabelX'],
            state_label_y=terms['StateLabelY'],
            primary_stratum_label=terms['PrimaryStratumLabel'],
            secondary_stratum_label=terms['SecondaryStratumLabel'],
            timestep_units=terms['TimestepUnits']
        )
    print('Imported terminology for project {}.'.format(project.name))

    # Import strata
    console.export_sheet('STSim_Stratum', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            Stratum.objects.create(
                stratum_id=int(row['ID']) if len(row['ID']) > 0 else -1,
                project=project,
                name=row['Name'],
                color=row['Color'],
                description=row['Description']
            )
    print('Imported strata for project {}.'.format(project.name))

    # import secondary strata
    console.export_sheet('STSim_SecondaryStratum', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            SecondaryStratum.objects.create(
                project=project,
                secondary_stratum_id=int(row['ID']) if len(row['ID']) > 0 else -1,
                name=row['Name'],
                description=row['Description']
            )
    print('Imported secondary strata for project {}.'.format(project.name))

    # import stateclasses
    console.export_sheet('STSim_StateClass', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            StateClass.objects.create(
                stateclass_id=int(row['ID']) if len(row['ID']) > 0 else -1,
                project=project,
                name=row['Name'],
                state_label_x=row['StateLabelXID'],
                state_label_y=row['StateLabelYID'],
                color=row['Color'],
                description=row['Description']
            )
    print('Imported state classes for project {}.'.format(project.name))

    # import transition types
    console.export_sheet('STSim_TransitionType', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            TransitionType.objects.create(
                project=project,
                transition_type_id=int(row['ID']) if len(row['ID']) > 0 else -1,
                name=row['Name'],
                color=row['Color'],
                description=row['Description']
            )
    print('Imported transition types for project {}.'.format(project.name))

    # import transition groups
    console.export_sheet('STSim_TransitionGroup', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            TransitionGroup.objects.create(
                project=project,
                name=row['Name'],
                description=row['Description']
            )
    print('Imported transition groups for project {}.'.format(project.name))

    # map transition groups to transition types
    console.export_sheet('STSim_TransitionTypeGroup', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            grp = TransitionGroup.objects.filter(name__exact=row['TransitionGroupID'], project=project).first()
            ttype = TransitionType.objects.filter(name__exact=row['TransitionTypeID'], project=project).first()
            TransitionTypeGroup.objects.create(
                project=project,
                transition_type=ttype,
                transition_group=grp,
                is_primary=row['IsPrimary']
            )
    print('Imported transition type groups for project {}.'.format(project.name))

    # import transition multiplier types
    console.export_sheet('STSim_TransitionMultiplierType', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            TransitionMultiplierType.objects.create(
                project=project,
                name=row['Name']
            )
    print('Imported transition multiplier types for project {}.'.format(project.name))

    # Import attribute groups
    console.export_sheet('STSim_AttributeGroup', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            AttributeGroup.objects.create(
                project=project,
                name=row['Name'],
                description=row['Description']
            )
    print('Imported attribute groups for project {}.'.format(project.name))

    # Import state attribute types
    console.export_sheet('STSim_StateAttributeType', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            StateAttributeType.objects.create(
                project=project,
                name=row['Name'],
                attribute_group=AttributeGroup.objects.filter(name__exact=row['AttributeGroupID'],
                                                              project=project).first(),
                units=row['Units'],
                description=row['Description']
            )
    print('Imported state attribute types for project {}.'.format(project.name))

    # Import transition attribute types
    console.export_sheet('STSim_TransitionAttributeType', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            TransitionAttributeType.objects.create(
                project=project,
                name=row['Name'],
                attribute_group=AttributeGroup.objects.filter(name__exact=row['AttributeGroupID'],
                                                              project=project).first(),
                units=row['Units'],
                description=row['Description']
            )
    print('Imported transition attribute types for project {}.'.format(project.name))

# TODO - size dist/priority, state/transition attributes/targets,
def process_scenario_inputs(console, scenario):

    tmp_file = get_random_csv(scenario.project.library.tmp_file)
    project = scenario.project
    kwgs = {'sid': scenario.sid, 'overwrite': True, 'orig': not scenario.is_result}

    # import initial run control
    console.export_sheet('STSim_RunControl', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        run_options = [r for r in reader][0]
        RunControl.objects.create(
            scenario=scenario,
            min_iteration=int(run_options['MinimumIteration']),
            max_iteration=int(run_options['MaximumIteration']),
            min_timestep=int(run_options['MinimumTimestep']),
            max_timestep=int(run_options['MaximumTimestep']),
            is_spatial=True if run_options['IsSpatial'] == 'Yes' else False
        )
    print('Imported (initial) run control for scenario {}'.format(scenario.sid))

    # import output options
    console.export_sheet('STSim_OutputOptions', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        output_options = [r for r in reader][0]
        for opt in output_options.keys():
            if len(output_options[opt]) > 0:  # a integer, or 'Yes', else ''
                if 'Timesteps' in opt:
                    timestep = int(output_options[opt])
                else:
                    timestep = -1  # default, won't be used
                enabled = True
            else:
                enabled = False
                timestep = -1
            OutputOption.objects.create(
                scenario=scenario,
                name=opt,
                timestep=timestep,
                enabled=enabled
            )
    print('Imported (initial) output options for scenario {}'.format(scenario.sid))

    console.export_sheet('STSim_DeterministicTransition', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            age_max = int(row['AgeMax']) if len(row['AgeMax']) > 0 else ''
            stratum_dest = row['StratumIDDest']
            t = DeterministicTransition.objects.create(
                scenario=scenario,
                stratum_src=Stratum.objects.filter(name__exact=row['StratumIDSource'],
                                                   project=project).first(),
                stratum_dest=Stratum.objects.filter(name__exact=row['StratumIDDest'],
                                                    project=project).first(),
                stateclass_src=StateClass.objects.filter(name__exact=row['StateClassIDSource'],
                                                         project=project).first(),
                stateclass_dest=StateClass.objects.filter(name__exact=row['StateClassIDDest'],
                                                          project=project).first(),
                age_min=int(row['AgeMin'])
            )
            if len(stratum_dest) > 0:
                t.stratum_dest = Stratum.objects.filter(name__exact=stratum_dest, project=project).first()
            if type(age_max) is int:
                t.age_max = age_max
            t.save()
    print('Imported deterministic transitions for scenario {}'.format(scenario.sid))

    # import initial probabilistic transition probabilities
    console.export_sheet('STSim_Transition', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            stratum_dest = row['StratumIDDest']
            t = Transition.objects.create(  # omit stratum_dest, no change in stratum per timestep
                scenario=scenario,
                stratum_src=Stratum.objects.filter(name__exact=row['StratumIDSource'],
                                                   project=project).first(),
                stateclass_src=StateClass.objects.filter(name__exact=row['StateClassIDSource'],
                                                         project=project).first(),
                stateclass_dest=StateClass.objects.filter(name__exact=row['StateClassIDDest'],
                                                          project=project).first(),
                transition_type=TransitionType.objects.filter(name__exact=row['TransitionTypeID'],
                                                              project=project).first(),
                probability=float(row['Probability']),
                age_reset=row['AgeReset']
            )
            if len(stratum_dest) > 0:
                t.stratum_dest = Stratum.objects.filter(name__exact=stratum_dest, project=project).first()
                t.save()

    print('Imported transition probabilities for scenario {}'.format(scenario.sid))

    # Import initial conditions non spatial configuration
    console.export_sheet('STSim_InitialConditionsNonSpatial', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        conditions = [r for r in reader][0]
        InitialConditionsNonSpatial.objects.create(
            scenario=scenario,
            total_amount=float(conditions['TotalAmount']),
            num_cells=int(conditions['NumCells']),
            calc_from_dist=conditions['CalcFromDist']
        )
    print('Imported (default) initial conditions configuration for scenario {}'.format(scenario.sid))

    # Import initial conditions non spatial values
    console.export_sheet('STSim_InitialConditionsNonSpatialDistribution', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            secondary_stratum = row['SecondaryStratumID']
            age_min = int(row['AgeMin']) if len(row['AgeMin']) > 0 else ''
            age_max = int(row['AgeMax']) if len(row['AgeMax']) > 0 else ''
            ic = InitialConditionsNonSpatialDistribution.objects.create(
                scenario=scenario,
                stratum=Stratum.objects.filter(name__exact=row['StratumID'],
                                                   project=project).first(),
                stateclass=StateClass.objects.filter(name__exact=row['StateClassID'],
                                                         project=project).first(),
                relative_amount=float(row['RelativeAmount'])
            )
            if type(age_min) is int:
                ic.age_min = age_min
            if type(age_max) is int:
                ic.age_max = age_max
            if len(secondary_stratum) > 0:
                ic.secondary_stratum = SecondaryStratum.objects.filter(name__exact=secondary_stratum,
                                                                       project=project).first()
            ic.save()
    print('Imported (default) initial conditions values for scenario {}'.format(scenario.sid))

    # Import transition targets
    console.export_sheet('STSim_TransitionTarget', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            secondary_stratum = row['SecondaryStratumID']
            iteration = int(row['Iteration']) if len(row['Iteration']) > 0 else ''
            timestep = int(row['Timestep']) if len(row['Timestep']) > 0 else ''
            tt = TransitionTarget.objects.create(
                scenario=scenario,
                stratum=Stratum.objects.filter(name__exact=row['StratumID'], project=project).first(),
                transition_group=TransitionGroup.objects.filter(name__exact=row['TransitionGroupID'],
                                                                project=project).first(),
                target_area=float(row['Amount'])
            )
            if type(iteration) is int:
                tt.iteration = iteration
            if type(timestep) is int:
                tt.timestep = timestep
            if len(secondary_stratum) > 0:
                tt.secondary_stratum = SecondaryStratum.objects.filter(name__exact=secondary_stratum,
                                                                       project=project).first()
            tt.save()
    print('Imported transition targets for scenario {}'.format(scenario.sid))

    # Import transition multiplier values
    console.export_sheet('STSim_TransitionMultiplierValue', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            stratum = row['StratumID']
            secondary_stratum = row['SecondaryStratumID']
            stateclass = row['StateClassID']
            iteration = int(row['Iteration']) if len(row['Iteration']) > 0 else ''
            timestep = int(row['Timestep']) if len(row['Timestep']) > 0 else ''
            transition_multiplier_type = row['TransitionMultiplierTypeID']
            tm = TransitionMultiplierValue.objects.create(
                scenario=scenario,
                transition_group=TransitionGroup.objects.filter(name__exact=row['TransitionGroupID'],
                                                                project=project).first(),
                multiplier=float(row['Amount'])
            )
            if len(stratum) > 0:
                tm.stratum = Stratum.objects.filter(name__exact=stratum, project=project).first()
            if len(secondary_stratum) > 0:
                tm.secondary_stratum = SecondaryStratum.objects.filter(name__exact=secondary_stratum,
                                                                       project=project).first()
            if len(stateclass) > 0:
                tm.stateclass = StateClass.objects.filter(name__exact=stateclass, project=project).first()
            if type(iteration) is int:
                tm.iteration = iteration
            if type(timestep) is int:
                tm.timestep = timestep
            if len(transition_multiplier_type) > 0:
                tm.transition_multiplier_type = TransitionMultiplierType.objects.filter(
                    name__exact=transition_multiplier_type, project=project).first()

            tm.save()
    print('Imported transition multiplier values for scenario {}'.format(scenario.sid))

    # Import transition size distribution
    console.export_sheet('STSim_TransitionSizeDistribution', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            iteration = int(row['Iteration']) if len(row['Iteration']) > 0 else ''
            timestep = int(row['Timestep']) if len(row['Timestep']) > 0 else ''
            stratum = row['StratumID']
            sd = TransitionSizeDistribution.objects.create(
                scenario=scenario,
                transition_group=TransitionGroup.objects.filter(name__exact=row['TransitionGroupID'],
                                                                project=project).first(),
                maximum_area=float(row['MaximumArea']),
                relative_amount=float(row['RelativeAmount'])
            )
            if type(iteration) is int:
                sd.iteration = iteration
            if type(timestep) is int:
                sd.timestep = timestep
            if len(stratum) > 0:
                sd.stratum = Stratum.objects.filter(name__exact=stratum, project=project).first()

            sd.save()
    print('Imported transition size distribution for scenario {}'.format(scenario.sid))

    # Import transition size prioritization
    console.export_sheet('STSim_TransitionSizePrioritization', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        priorities = [r for r in reader]
        if len(priorities) > 0:
            priorities = priorities[0]
            iteration = int(priorities['Iteration']) if len(priorities['Iteration']) > 0 else ''
            timestep = int(priorities['Timestep']) if len(priorities['Timestep']) > 0 else ''
            stratum = priorities['StratumID']
            transition_group = priorities['TransitionGroupID']
            sp = TransitionSizePrioritization.objects.create(
                scenario=scenario,
                priority=priorities['Priority']
            )
            if len(stratum) > 0:
                sp.stratum = Stratum.objects.filter(name__exact=stratum, project=project).first()
            if len(transition_group) > 0:
                sp.transition_group = TransitionGroup.objects.filter(name__exact=transition_group,
                                                                     project=project).first()
            if type(iteration) is int:
                sp.iteration = iteration
            if type(timestep) is int:
                sp.timestep = timestep

            sp.save()
    print('Imported transition size prioritization for scenario {}'.format(scenario.sid))

    # TODO - Import transition spatial multiplier configuration, and if is result, process web outputs

    # Import state attribute values
    console.export_sheet('STSim_StateAttributeValue', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            iteration = int(row['Iteration']) if len(row['Iteration']) > 0 else ''
            timestep = int(row['Timestep']) if len(row['Timestep']) > 0 else ''
            stratum = row['StratumID']
            secondary_stratum = row['SecondaryStratumID']
            stateclass = row['StateClassID']
            sav = StateAttributeValue.objects.create(
                scenario=scenario,
                state_attribute_type=StateAttributeType.objects.filter(
                    name__exact=row['StateAttributeTypeID'], project=project).first(),
                value=float(row['Value'])
            )
            if len(stratum) > 0:
                sav.stratum = Stratum.objects.filter(name__exact=stratum, project=project).first()
            if len(secondary_stratum) > 0:
                sav.secondary_stratum = SecondaryStratum.objects.filter(name__exact=secondary_stratum,
                                                                        project=project).first()
            if len(stateclass) > 0:
                sav.stateclass = StateClass.objects.filter(name__exact=stateclass, project=project).first()
            if type(iteration) is int:
                sav.iteration = iteration
            if type(timestep) is int:
                sav.timestep = timestep

            sav.save()
    print('Imported state attribute values for scenario {}'.format(scenario.sid))

    # import transition attribute values
    console.export_sheet('STSim_TransitionAttributeValue', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            iteration = int(row['Iteration']) if len(row['Iteration']) > 0 else ''
            timestep = int(row['Timestep']) if len(row['Timestep']) > 0 else ''
            stratum = row['StratumID']
            secondary_stratum = row['SecondaryStratumID']
            stateclass = row['StateClassID']
            tav = TransitionAttributeValue.objects.create(
                scenario=scenario,
                transition_group=TransitionGroup.objects.filter(
                    name__exact=row['TransitionGroupID'], project=project).first(),
                transition_attribute_type=TransitionAttributeType.objects.filter(
                    name__exact=row['TransitionAttributeTypeID'], project=project).first(),
                value=float(row['Value'])
            )
            if len(stratum) > 0:
                tav.stratum = Stratum.objects.filter(name__exact=stratum, project=project).first()
            if len(secondary_stratum) > 0:
                tav.secondary_stratum = SecondaryStratum.objects.filter(name__exact=secondary_stratum,
                                                                        project=project).first()
            if len(stateclass) > 0:
                tav.stateclass = StateClass.objects.filter(name__exact=stateclass, project=project).first()
            if type(iteration) is int:
                tav.iteration = iteration
            if type(timestep) is int:
                tav.timestep = timestep

            tav.save()
    print('Imported transition attribute values for scenario {}'.format(scenario.sid))

    # import transition attribute targets
    console.export_sheet('STSim_TransitionAttributeTarget', tmp_file, **kwgs)
    with open(tmp_file, 'r') as sheet:
        reader = csv.DictReader(sheet)
        for row in reader:
            iteration = int(row['Iteration']) if len(row['Iteration']) > 0 else ''
            timestep = int(row['Timestep']) if len(row['Timestep']) > 0 else ''
            stratum = row['StratumID']
            secondary_stratum = row['SecondaryStratumID']
            tat = TransitionAttributeTarget.objects.create(
                scenario=scenario,
                transition_attribute_type=TransitionAttributeType.objects.filter(
                    name__exact=row['TransitionAttributeTypeID'], project=project).first(),
                target=float(row['Amount'])
            )
            if len(stratum) > 0:
                tat.stratum = Stratum.objects.filter(name__exact=stratum, project=project).first()
            if len(secondary_stratum) > 0:
                tat.secondary_stratum = SecondaryStratum.objects.filter(name__exact=secondary_stratum,
                                                                        project=project).first()
            if type(iteration) is int:
                tat.iteration = iteration
            if type(timestep) is int:
                tat.timestep = timestep

            tat.save()
    print('Imported transition attribute targets for scenario {}'.format(scenario.sid))

    # TODO - Determine whether this scenario is a dependency of another scenario, or has dependencies that rely on this

    if os.path.exists(tmp_file):
        os.remove(tmp_file)