"""
Async Exception Handler for NeuraOps Agent

Handles asyncio exceptions with proper CancelledError re-raising.
Ensures correct async cancellation patterns.
"""
import asyncio
import logging
from typing import Optional


class AsyncExceptionHandler:
    """
    Gestionnaire d'exceptions async avec re-raise correct des CancelledError
    
    Gestion centralisée des exceptions async
    Ensures CancelledError is properly re-raised
    """
    
    @staticmethod
    async def handle_task_cancellation(
        task: Optional[asyncio.Task], 
        task_name: str, 
        logger: logging.Logger
    ) -> None:
        """
        Gère l'annulation d'une tâche avec cleanup approprié
        
        Simple task cancellation with proper re-raise
        Always re-raises CancelledError after cleanup
        
        Args:
            task: Tâche à annuler
            task_name: Nom de la tâche pour les logs
            logger: Logger pour traçabilité
        """
        if not task or task.done():
            return
            
        logger.debug(f"Cancelling task: {task_name}")
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            logger.debug(f"Task {task_name} cancelled successfully")
            raise  # Re-raise obligatoire pour propagation correcte
        except Exception as e:
            logger.error(f"Error during {task_name} cleanup: {e}")
            raise
    
    @staticmethod
    async def cleanup_task_set(
        tasks: set, 
        logger: logging.Logger
    ) -> None:
        """
        Nettoie un ensemble de tâches
        
        Batch task cleanup
        Proper cancellation for multiple tasks
        Fixes S7483: Remove timeout parameter - caller uses asyncio.wait_for()
        
        Args:
            tasks: Ensemble de tâches à nettoyer
            logger: Logger pour traçabilité  
        """
        if not tasks:
            return
            
        logger.debug(f"Cleaning up {len(tasks)} tasks")
        
        # Cancel all tasks
        for task in tasks:
            if not task.done():
                task.cancel()
        
        # Wait for cancellation - caller handles timeout with asyncio.wait_for()
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            logger.debug("Task cleanup cancelled")
            raise  # Re-raise pour propagation
        
        logger.debug("Task cleanup completed")