"""
Task Manager for NeuraOps Agent

Centralized asyncio task management with proper reference handling.
Saves task references to prevent garbage collection.
"""
import asyncio
import logging
import weakref
from typing import Set, Optional, Callable, Any
from .agent_exceptions import AsyncExceptionHandler


class TaskManager:
    """
    Gestionnaire centralisé de tâches asyncio avec références sauvegardées
    
    Gestionnaire centralisé pour tâches background
    Saves task references to prevent premature GC
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize task manager
        
        Args:
            logger: Logger pour traçabilité des tâches
        """
        self.logger = logger
        self.tasks: Set[asyncio.Task] = set()  # Sauvegarde des références
        self.exception_handler = AsyncExceptionHandler()
        
    def create_task(self, coro, name: str = None) -> asyncio.Task:
        """
        Crée et sauvegarde une tâche avec nom
        
        Simple task creation with reference saving
        Task reference saved in self.tasks set
        
        Args:
            coro: Coroutine à exécuter
            name: Nom optionnel de la tâche
            
        Returns:
            Task créée et sauvegardée
        """
        task = asyncio.create_task(coro, name=name)
        self.tasks.add(task)
        
        # Auto-cleanup when task completes
        task.add_done_callback(self._cleanup_completed_task)
        
        self.logger.debug(f"Created task: {name or 'unnamed'} ({id(task)})")
        return task
    
    def create_fire_and_forget_task(
        self, 
        coro, 
        name: str = None, 
        error_callback: Optional[Callable[[Exception], None]] = None
    ) -> asyncio.Task:
        """
        Crée une tâche "fire-and-forget" avec gestion d'erreur
        
        Fire-and-forget task execution with error handling
        Fixes S7502: Reference saved même pour tâches indépendantes
        
        Args:
            coro: Coroutine à exécuter
            name: Nom de la tâche
            error_callback: Callback optionnel pour erreurs
            
        Returns:
            Task créée
        """
        task = self.create_task(coro, name)
        
        def handle_completion(completed_task: asyncio.Task):
            try:
                if completed_task.cancelled():
                    self.logger.debug(f"Fire-and-forget task cancelled: {name}")
                    return
                    
                # Check for exceptions
                exception = completed_task.exception()
                if exception:
                    self.logger.error(f"Error in fire-and-forget task {name}: {exception}")
                    if error_callback:
                        error_callback(exception)
                else:
                    self.logger.debug(f"Fire-and-forget task completed: {name}")
                    
            except Exception as e:
                self.logger.error(f"Error in task completion handler: {e}")
        
        task.add_done_callback(handle_completion)
        return task
    
    async def cancel_all(self) -> None:
        """
        Annule toutes les tâches avec timeout context manager
        
        Cancel all managed tasks properly
        Fixes S7483: Uses asyncio.wait_for context manager instead of timeout parameter
        Fixes S7497: Uses AsyncExceptionHandler for proper CancelledError handling
        """
        if not self.tasks:
            self.logger.debug("No tasks to cancel")
            return
            
        self.logger.info(f"Cancelling {len(self.tasks)} tasks...")
        
        try:
            # S7483: Use timeout context manager instead of parameter
            await asyncio.wait_for(
                self.exception_handler.cleanup_task_set(
                    self.tasks.copy(), 
                    self.logger
                ),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            self.logger.warning("Task cancellation timed out after 5 seconds")
            # Force cleanup remaining tasks
            for task in self.tasks.copy():
                if not task.done():
                    task.cancel()
        
        # Clear the set
        self.tasks.clear()
        self.logger.info("All tasks cancelled and cleaned up")
    
    async def cancel_task_by_name(self, task_name: str) -> bool:
        """
        Annule une tâche par son nom
        
        Cancel specific task by name
        
        Args:
            task_name: Nom de la tâche à annuler
            
        Returns:
            True si tâche trouvée et annulée
        """
        # S7504: Use copy() instead of list() for safe iteration during modification
        for task in self.tasks.copy():
            if task.get_name() == task_name:
                await self.exception_handler.handle_task_cancellation(
                    task, task_name, self.logger
                )
                return True
                
        self.logger.warning(f"Task not found for cancellation: {task_name}")
        return False
    
    def get_running_tasks_count(self) -> int:
        """
        Retourne le nombre de tâches en cours
        
        Get running tasks count
        
        Returns:
            Nombre de tâches actives
        """
        running_count = sum(1 for task in self.tasks if not task.done())
        return running_count
    
    def _cleanup_completed_task(self, task: asyncio.Task) -> None:
        """
        Nettoie une tâche terminée (callback interne)
        
        Internal cleanup callback for completed tasks
        
        Args:
            task: Tâche terminée à nettoyer
        """
        self.tasks.discard(task)
        self.logger.debug(f"Cleaned up completed task: {task.get_name() or 'unnamed'}")