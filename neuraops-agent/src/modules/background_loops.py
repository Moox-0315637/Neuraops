"""
Background Loops for NeuraOps Agent

Handles metrics and heartbeat loops with proper CancelledError handling.
Ensures correct asyncio cancellation patterns.
"""
import asyncio
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..agent import Agent
    from ..connector import CoreConnector
    from ..collector import MetricsCollector


class BackgroundLoops:
    """
    Gestionnaire des loops background avec gestion d'exceptions correcte
    
    Background task loops management
    Proper CancelledError re-raising in all loops
    """
    
    def __init__(self):
        """Initialize background loops manager"""
        self.logger = logging.getLogger(__name__)
    
    async def metrics_loop(
        self, 
        agent: 'Agent', 
        collector: 'MetricsCollector', 
        connector: Optional['CoreConnector']
    ) -> None:
        """
        Loop de collecte et envoi des métriques
        
        Metrics collection with proper error handling
        Proper CancelledError re-raising
        
        Args:
            agent: Instance de l'agent pour vérifier running state
            collector: Collecteur de métriques
            connector: Connecteur vers le Core (peut être None)
        """
        self.logger.info("Starting metrics loop")
        
        try:
            while agent.running:
                try:
                    # Collect metrics
                    metrics = collector.collect_all()
                    self.logger.debug(f"Collected metrics: {len(metrics)} items")
                    
                    # Send to core if connected
                    if connector:
                        await connector.send_metrics(metrics)
                        self.logger.debug("Metrics sent to Core")
                    else:
                        self.logger.warning("No connector available, metrics not sent")
                    
                    # Wait for next collection
                    await asyncio.sleep(agent.config.metrics_interval)
                    
                except asyncio.CancelledError:
                    self.logger.debug("Metrics loop cancelled")
                    raise  # Re-raise obligatoire pour propagation correcte
                    
                except Exception as e:
                    self.logger.error(f"Error in metrics loop: {e}")
                    # Short retry delay on error
                    await asyncio.sleep(5)
                    
        except asyncio.CancelledError:
            self.logger.info("Metrics loop cancelled during shutdown")
            raise  # Re-raise pour propagation
            
        finally:
            self.logger.info("Metrics loop stopped")
    
    async def heartbeat_loop(
        self, 
        agent: 'Agent', 
        connector: Optional['CoreConnector']
    ) -> None:
        """
        Loop d'envoi de heartbeat vers le Core
        
        Heartbeat with proper error handling
        Proper CancelledError re-raising
        
        Args:
            agent: Instance de l'agent pour vérifier running state
            connector: Connecteur vers le Core (peut être None)
        """
        self.logger.info("Starting heartbeat loop")
        
        try:
            while agent.running:
                try:
                    if connector:
                        await connector.send_heartbeat()
                        self.logger.debug("Heartbeat sent to Core")
                    else:
                        self.logger.warning("No connector available, heartbeat not sent")
                    
                    await asyncio.sleep(agent.config.heartbeat_interval)
                    
                except asyncio.CancelledError:
                    self.logger.debug("Heartbeat loop cancelled")
                    raise  # Re-raise obligatoire
                    
                except Exception as e:
                    self.logger.error(f"Error in heartbeat loop: {e}")
                    # Longer retry delay for heartbeat errors
                    await asyncio.sleep(10)
                    
        except asyncio.CancelledError:
            self.logger.info("Heartbeat loop cancelled during shutdown")
            raise  # Re-raise pour propagation
            
        finally:
            self.logger.info("Heartbeat loop stopped")
    
    async def command_loop(
        self, 
        agent: 'Agent', 
        connector: Optional['CoreConnector'],
        command_handler
    ) -> None:
        """
        Loop principal de gestion des commandes
        
        Command handling with proper error handling
        Proper CancelledError re-raising
        
        Args:
            agent: Instance de l'agent
            connector: Connecteur vers le Core
            command_handler: Handler pour traitement des commandes
        """
        self.logger.info("Starting command loop")
        
        try:
            while agent.running:
                try:
                    if not connector:
                        await asyncio.sleep(1)
                        continue
                    
                    # Check for incoming commands
                    command = await connector.receive_command()
                    
                    if command:
                        self.logger.debug(f"Received command: {command.get('type', 'unknown')}")
                        # Handle command using task manager to fix S7502
                        # S7503 fix: command_handler is now synchronous (no await needed)
                        command_handler(command)
                    
                    # Small delay to prevent busy waiting
                    await asyncio.sleep(0.1)
                    
                except asyncio.CancelledError:
                    self.logger.debug("Command loop cancelled")
                    raise  # Re-raise obligatoire
                    
                except Exception as e:
                    self.logger.error(f"Error in command loop: {e}")
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            self.logger.info("Command loop cancelled during shutdown") 
            raise  # Re-raise pour propagation
            
        finally:
            self.logger.info("Command loop stopped")
    
    def start_all_loops(  # S7503: Remove async keyword - no await used
        self, 
        agent: 'Agent', 
        collector: 'MetricsCollector',
        connector: Optional['CoreConnector'],
        command_handler,
        task_manager
    ) -> None:
        """
        Démarre tous les loops background via task manager
        
        Start all loops with proper task management
        Fixes S7502: Uses task manager for proper reference handling
        Fixes S7503: Synchronous function - no async keyword needed
        
        Args:
            agent: Instance de l'agent
            collector: Collecteur de métriques
            connector: Connecteur vers le Core
            command_handler: Handler pour commandes
            task_manager: Gestionnaire de tâches
        """
        self.logger.info("Starting all background loops")
        
        # Create tasks via task manager (fixes S7502)
        metrics_task = task_manager.create_task(
            self.metrics_loop(agent, collector, connector),
            "metrics_loop"
        )
        
        heartbeat_task = task_manager.create_task(
            self.heartbeat_loop(agent, connector),
            "heartbeat_loop"
        )
        
        command_task = task_manager.create_task(
            self.command_loop(agent, connector, command_handler),
            "command_loop"
        )
        
        self.logger.info("All background loops started")
        
        # Store references in agent for external access if needed
        agent.metrics_task = metrics_task
        agent.heartbeat_task = heartbeat_task
        agent.command_task = command_task