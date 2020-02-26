import logging

from click import style

from zygoat.utils.files import repository_root
from zygoat.config import Config
from zygoat.constants import Phases

log = logging.getLogger()


class Component:
    def __init__(self, parent=None, sub_components=[]):
        self.sub_components = []

        self.reload()
        self.parent = parent

        for component in sub_components:
            component.parent = self.identifier
            self.sub_components.append(component)

    @property
    def name(self):
        """
        Convenience function for retrieving the class name
        """
        return self.__class__.__name__

    @property
    def identifier(self):
        """
        The component's path in the tree, using django notation

        (i.e. Backend__Linting, Backend__Dockerfile, Frontend__Tests, etc.)
        """
        if self.parent is None:
            return self.name

        return f'{self.parent}__{self.name}'

    @property
    def exclude(self):
        """
        Whether or not this sub-component should be used in the project
        """
        if self.config.get('exclude', None) is None:
            return False

        return self.identifier in self.config.exclude

    @property
    def include(self):
        """
        Convenience wrapper for easier reading
        """
        return not self.exclude

    def call_phase(self, phase, force_create=False):
        """
        Calls a phase (e.g. create, update, delete) on self + all sub components
        """
        if self.exclude:
            log.debug(f'Skipping {self.identifier} as it was found in the exclude list')
            return

        self.reload()

        log_string = 'Calling phase {} for {}'
        phase_func = getattr(self, phase, None)

        is_create = phase == Phases.CREATE

        if phase_func is not None:
            with repository_root():
                if is_create and self.installed and not force_create:
                    styled_name = style(self.identifier, bold=True, fg='cyan')
                    log.warning(f'Component {styled_name} is already installed, skipping')
                else:
                    log.debug(log_string.format(phase, self.__class__.__name__))
                    phase_func()

        for component in self.sub_components:
            log.debug(log_string.format(phase, component.__class__.__name__))
            component.call_phase(phase, force_create=force_create)

    @property
    def installed(self):
        """
        Halts the create phase if True
        """
        return False

    def list(self):
        """
        Prints the identifier of this component for exclusion filtering
        """
        if self.include:
            print(self.identifier)

    def reload(self):
        """
        Reloads the configuration file
        """
        self.config = Config()

        for component in self.sub_components:
            component.parent = self.identifier