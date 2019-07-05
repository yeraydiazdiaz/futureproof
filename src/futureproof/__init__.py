from .task_manager import TaskManager, ErrorPolicyEnum
from .executors import ThreadPoolExecutor, ProcessPoolExecutor

__version__ = "0.2.0"

__title__ = "futureproof"
__description__ = "Bulletproof concurrent.futures"
__url__ = "https://github.com/yeraydiazdiaz/futureproof"
__uri__ = __url__
__doc__ = __description__ + " <" + __uri__ + ">"

__author__ = "Yeray Díaz Díaz"
__email__ = "yeraydiazdiaz@gmail.com"

__license__ = "MIT"
__copyright__ = "Copyright (c) 2019 Yeray Díaz Díaz"


__all__ = [
    "TaskManager",
    "ErrorPolicyEnum",
    "ThreadPoolExecutor",
    "ProcessPoolExecutor",
]
