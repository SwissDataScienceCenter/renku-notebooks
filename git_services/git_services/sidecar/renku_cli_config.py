from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict

from renku.command.command_builder.command import Command, CommandResult
from renku.command.save import save_and_push_command


class RenkuCommandName(Enum):
    """Valid and supported renku command names."""

    save = "save"

    @classmethod
    def get_all_names(cls):
        return [i.name for i in cls]

    @classmethod
    def get_all_values(cls):
        return [i.value for i in cls]


@dataclass
class RenkuCliCommand:
    """Basic representation of a renku cli command, with the builder and a serializer."""

    name: RenkuCommandName
    command: Command
    output_serializer: Callable[[CommandResult], str]


renku_cli_config: Dict[RenkuCommandName, RenkuCliCommand] = {
    RenkuCommandName.save: RenkuCliCommand(
        RenkuCommandName.save, save_and_push_command, lambda x: str(x.output)
    ),
}
