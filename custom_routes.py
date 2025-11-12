"""
@author: Hmily
@title: comfy-deploy
@nickname: comfy-deploy
@description: Easy deploy API for ComfyUI.
"""

import uuid
import asyncio
import logging
import server
import execution
from aiohttp import web
from queue import Queue
import time
import httpx
import random
from typing import Any, Tuple, Optional
from collections import defaultdict


# ========================= Configuration and Initialization =========================

class Config:
    ENABLE_CUSTOM_EVENT_HANDLING = True
    ENABLE_VERBOSE_LOGGING = False
    # Progress update minimum interval time(seconds)
    PROGRESS_THROTTLE_INTERVAL = 0.5

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("comfy-deploy")

# Suppress logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


class TaskManager:
    def __init__(self):
        # Workflow progress tracking
        self.workflow_nodes = {}  # prompt_id -> {total nodes, completed nodes, node list}
        self.workflow_progress = {}  # prompt_id -> {total percent, current node}
        
        # Throttling control
        self.progress_throttle = {}  # prompt_id -> last time of progress update
        
        # Callback task management
        self.callback_urls = {}  # prompt_id -> callback_url
        self.client_prompts = {}  # client_id -> prompt_id mapping, for event association
        
        # API created tasks list
        self.api_created_tasks = set()  # store task IDs created through API
        
        # Store task outputs
        self.execution_outputs = {}  # prompt_id -> {outputs: {}}

    def is_api_task(self, prompt_id: str) -> bool:
        if prompt_id in self.api_created_tasks:
            return True

        # Check if there is a callback URL (only API tasks have callback URLs)
        if prompt_id in self.callback_urls:
            return True

        if prompt_id in [mapped_id for mapped_id in self.client_prompts.values()]:
            return True

        return False

    def cleanup_task(self, prompt_id: str) -> None:
        self.workflow_nodes.pop(prompt_id, None)
        self.workflow_progress.pop(prompt_id, None)
        
        self.progress_throttle.pop(prompt_id, None)
        
        self.callback_urls.pop(prompt_id, None)
        
        if prompt_id in self.api_created_tasks:
            self.api_created_tasks.remove(prompt_id)
        
        self.execution_outputs.pop(prompt_id, None)
        
        for client_id, mapped_prompt_id in list(self.client_prompts.items()):
            if mapped_prompt_id == prompt_id:
                self.client_prompts.pop(client_id, None)

class WebSocketManager:
    def __init__(self):
        self.task_listeners = defaultdict(list)  # prompt_id -> list of websockets
        self.machine_listeners = {}  # machine_id -> websocket, manage WebSocket connections by machine ID
        self.machine_prompts = defaultdict(set)  # machine_id -> set of prompt_ids
        
        self.ws_event_queue = Queue()


config = Config()
task_manager = TaskManager()
ws_manager = WebSocketManager()

def check_event_handling() -> bool:
    return config.ENABLE_CUSTOM_EVENT_HANDLING

def check_verbose_logging() -> bool:
    return config.ENABLE_VERBOSE_LOGGING

# ========================= Event handling system =========================
class EventHandler:
    """Event handler, responsible for registering and dispatching events"""
    
    def __init__(self):
        self.event_callbacks = {}

    def register_event(self, event_name: str, callback: callable) -> None:
        """
        Register a callback function for a specified event
        
        Parameters:
            event_name: event name
            callback: callback function, receive event data as parameter
        """
        if event_name not in self.event_callbacks:
            self.event_callbacks[event_name] = []
        self.event_callbacks[event_name].append(callback)
        if check_verbose_logging():
            logger.info(f"[EventHandler] Register event: {event_name}")

    def handle_event(self, event_name: str, data: Any) -> None:
        """
        Handle events, call all registered callback functions
        
        Parameters:
            event_name: event name
            data: event data
        """
        if not check_event_handling():
            return

        str_event_name = str(event_name)

        log_event = True
        if "crystools.monitor" in str_event_name:
            log_event = False

        if log_event and check_verbose_logging():
            logger.info(f"[EventHandler] Received event: {str_event_name}, data: {str(data)[:100]}...")

        if str_event_name in self.event_callbacks:
            for callback in self.event_callbacks[str_event_name]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"[EventHandler] Error handling event {str_event_name}: {str(e)}")
        elif log_event and check_verbose_logging():
            logger.warning(f"[EventHandler] Received unregistered event: {str_event_name}")

event_handler = EventHandler()


# ========================= Basic event handling function =========================
def handle_execution_events(event_name: str, data: dict) -> None:
    if not check_event_handling():
        return

    if event_name == "execution_start":
        # Task started executing
        prompt_id = data.get("prompt_id")
        if prompt_id:
            print(f"[Event] Task started executing: {prompt_id}")

    elif event_name == "execution_cached":
        # Execute task from cache
        prompt_id = data.get("prompt_id")
        nodes = data.get("nodes", [])
        if prompt_id:
            print(f"[Event] Execute task from cache: {prompt_id}, cache nodes: {len(nodes)}")

    elif event_name == "executing":
        # Node is executing
        prompt_id = data.get("prompt_id")
        node = data.get("node")
        if prompt_id:
            print(f"[Event] Node executing: {prompt_id}, node: {node}")

    elif event_name == "executed":
        # Node executed
        prompt_id = data.get("prompt_id")
        node = data.get("node")
        if prompt_id:
            print(f"[Event] Node executed: {prompt_id}, node: {node}")

    elif event_name == "execution_error":
        # Execution error
        prompt_id = data.get("prompt_id")
        error_msg = data.get("exception_message", "Unknown error")
        if prompt_id:
            print(f"[Event] Execution error: {prompt_id}, error: {error_msg}")

    elif event_name == "execution_success":
        # Execution success
        prompt_id = data.get("prompt_id")
        if prompt_id:
            print(f"[Event] Execution success: {prompt_id}")


# ========================= Advanced event handling and callback =========================
def handle_execution_events_with_ws_and_callback(event_name: str, data: dict) -> None:
    """
    Handle execution events and send notifications through WebSocket and callback URL
    
    Parameters:
        event_name: event name
        data: event data
    """
    if not check_event_handling():
        return

    if check_verbose_logging():
        logger.info(f"[Event handling] Handle event: {event_name}, data: {str(data)[:100]}...")

    prompt_id = data.get("prompt_id")
    client_id = data.get("client_id")

    if not prompt_id and client_id and client_id in task_manager.client_prompts:
        prompt_id = task_manager.client_prompts[client_id]
        data["prompt_id"] = prompt_id

    if not prompt_id:
        if client_id:
            if check_verbose_logging():
                logger.warning(f"[Event handling] Event {event_name} only has client_id without prompt_id: {client_id}")
        else:
            if check_verbose_logging():
                logger.warning(f"[Event handling] Event {event_name} has no associated prompt_id or client_id")
        return
        
    if not task_manager.is_api_task(prompt_id):
        return

    # Track workflow progress
    _update_workflow_progress(event_name, prompt_id, client_id, data)

    ws_manager.ws_event_queue.put((prompt_id, event_name, data))

    callback_data = _prepare_callback_data(event_name, prompt_id, client_id, data)
    
    if callback_data:
        callback_event, event_data = callback_data
        
        if callback_event and event_data and prompt_id in task_manager.callback_urls:
            ws_manager.ws_event_queue.put((prompt_id, "callback", (callback_event, event_data)))
            
        # Clean up client_id mapping (if task is completed)
        if event_name in ["execution_success", "execution_error"] and client_id and client_id in task_manager.client_prompts:
            logger.info(f"[Event handling] Task completed, clean up client_id mapping: {client_id} -> {prompt_id}")
            task_manager.client_prompts.pop(client_id, None)


def _update_workflow_progress(event_name: str, prompt_id: str, client_id: str, data: dict) -> None:
    """
    Update task progress and node execution status
    
    Parameters:
        event_name: event name
        prompt_id: task ID
        client_id: client ID
        data: event data
    """


    if event_name == "execution_start":
        try:
            prompt_server = server.PromptServer.instance
            queued_prompts = prompt_server.prompt_queue.get_current_queue()

            workflow_prompt = None
            for queue_item in queued_prompts[0] + queued_prompts[1]:  # current executing + waiting queue
                if queue_item[1] == prompt_id:
                    workflow_prompt = queue_item[2]  # get workflow definition
                    break

            if workflow_prompt:
                task_manager.workflow_nodes[prompt_id] = {
                    "total": len(workflow_prompt),
                    "completed": 0,
                    "nodes": list(workflow_prompt.keys()),
                    "active_node": None,
                    "workflow_definition": workflow_prompt  # save full workflow definition
                }
                task_manager.workflow_progress[prompt_id] = {
                    "percent": 0,
                    "current_node": None,
                    "node_progress": {},  # record progress of each node
                    "execution_order": []  # record node execution order
                }
                logger.info(f"[comfy-deploy] Task started executing {prompt_id} contains {len(workflow_prompt)} nodes")
            else:
                task_manager.workflow_nodes[prompt_id] = {
                    "total": 100, "completed": 0, "nodes": [], 
                    "active_node": None, "workflow_definition": {}
                }
                task_manager.workflow_progress[prompt_id] = {
                    "percent": 0, "current_node": None, 
                    "node_progress": {}, "execution_order": []
                }
        except Exception as e:
            logger.error(f"[comfy-deploy] Error initializing task {prompt_id} progress tracking: {str(e)}")
            task_manager.workflow_nodes[prompt_id] = {
                "total": 100, "completed": 0, "nodes": [], 
                "active_node": None, "workflow_definition": {}
            }
            task_manager.workflow_progress[prompt_id] = {
                "percent": 0, "current_node": None, 
                "node_progress": {}, "execution_order": []
            }

        task_manager.execution_outputs[prompt_id] = {'outputs': {}}
        ws_manager.ws_event_queue.put((prompt_id, "callback", ("task_started", {
            "prompt_id": prompt_id,
            "client_id": client_id,
            "status": "running",
            "progress": 0,
            "message": "Task started executing",
            "timestamp": int(time.time())
        })))

    elif event_name == "executing":
        # Node started executing
        node = data.get("node")
        if prompt_id in task_manager.workflow_progress and node:
            # Record current executing node
            task_manager.workflow_progress[prompt_id]["current_node"] = node
            task_manager.workflow_nodes[prompt_id]["active_node"] = node

            # Add to execution order list (if not duplicate)
            if node not in task_manager.workflow_progress[prompt_id]["execution_order"]:
                task_manager.workflow_progress[prompt_id]["execution_order"].append(node)

            # When node starts executing, increase the number of executed nodes (if this node is not recorded before)
            if node not in task_manager.workflow_progress[prompt_id].get("node_progress", {}):
                task_manager.workflow_nodes[prompt_id]["completed"] += 1

            task_manager.workflow_progress[prompt_id]["node_progress"][node] = {
                "value": 0, "max": 100, "percent": 0
            }

            total_nodes = task_manager.workflow_nodes[prompt_id]["total"]
            completed_nodes = task_manager.workflow_nodes[prompt_id]["completed"]

            if total_nodes <= 0:
                total_nodes = 1

            progress_percent = min(100, int(((completed_nodes-1) * 100) / total_nodes))
            task_manager.workflow_progress[prompt_id]["percent"] = progress_percent

            logger.info(f"[comfy-deploy] Task {prompt_id} started executing node {node}, total progress: {progress_percent}%")
            send_workflow_progress_callback(prompt_id, client_id)

    elif event_name == "executed":
        # Node executed, update progress
        node = data.get("node")
        if prompt_id in task_manager.workflow_nodes and prompt_id in task_manager.workflow_progress and node:
            task_manager.workflow_progress[prompt_id]["node_progress"][node] = {
                "value": 100, "max": 100, "percent": 100
            }

            task_manager.execution_outputs[prompt_id]['outputs'][node] = data.get('output', {})

            logger.info(f"[comfy-deploy] Task {prompt_id} node {node} executed, total progress: {task_manager.workflow_progress[prompt_id]['percent']}%")

            task_manager.workflow_nodes[prompt_id]["active_node"] = None

            send_workflow_progress_callback(prompt_id, client_id)

    elif event_name in ["execution_success", "execution_error"]:
        if prompt_id in task_manager.workflow_progress:
            task_manager.workflow_progress[prompt_id]["percent"] = 100
            send_workflow_progress_callback(prompt_id, client_id)

        logger.info(f"[comfy-deploy] Task {prompt_id} execution ended! Status: {event_name}")

def _prepare_callback_data(event_name: str, prompt_id: str, client_id: str, data: dict) -> Optional[Tuple]:
    """
    Prepare callback data based on event type
    
    Parameters:
        event_name: event name
        prompt_id: task ID
        client_id: client ID
        data: event data
        
    Returns:
        Tuple (callback_event, callback_data) or None
    """
    callback_event = None
    callback_data = None

    if event_name == "execution_start":
        callback_event = "task_started"
        callback_data = {
            "prompt_id": prompt_id,
            "client_id": client_id,
            "status": "running",
            "progress": 0,
            "message": "Task started executing",
            "timestamp": int(time.time())
        }
        if check_verbose_logging():
            logger.info(f"[Event handling] Prepare to send task started callback: {prompt_id}")
            
    elif event_name in ["execution_success", "execution_error"]:
        # Handle task completion event (whether successful or failed)
        is_success = event_name == "execution_success"
        error_msg = data.get("exception_message", "unknown error") if not is_success else None

        # Get output data (if the task is successfully completed)
        result_data = {'images': [], 'videos': []}
        if is_success:
            try:
                history_data = task_manager.execution_outputs[prompt_id]
                outputs = history_data.get('outputs', {})
                for output in outputs.values():
                    if output:
                        for k, v in output.items():
                            if 'images' in k:
                                result_data['images'].extend(v)
                            elif 'videos' in k or 'gifs' in k:
                                result_data['videos'].extend(v)
                if check_verbose_logging():
                    logger.info(f"[Event handling] Get output of task {prompt_id}: {len(outputs)} nodes")
            except Exception as e:
                logger.error(f"[Event handling] Error getting output of task {prompt_id}: {str(e)}")

        if is_success:
            callback_event = "task_success"
            callback_data = {
                "prompt_id": prompt_id,
                "client_id": client_id,
                "status": "success",
                "progress": 100,
                "message": "Task executed successfully",
                "result": result_data,
                "raw_outputs": outputs,
                "timestamp": int(time.time())
            }
            if check_verbose_logging():
                logger.info(f"[Event handling] Prepare to send task success callback: {prompt_id}")
        else:
            callback_event = "task_failed"
            callback_data = {
                "prompt_id": prompt_id,
                "client_id": client_id,
                "status": "failed",
                "progress": 0,
                "message": f"Task executed failed: {error_msg}",
                "error": error_msg,
                "timestamp": int(time.time())
            }
            if check_verbose_logging():
                logger.info(f"[Event handling] Prepare to send task failed callback: {prompt_id}, error: {error_msg}")

    return (callback_event, callback_data) if callback_event else None


# ========================= Progress tracking and throttling control =========================
def send_workflow_progress_callback(prompt_id: str, client_id: str) -> None:
    """
    Send workflow progress callback, including node execution information
    
    Parameters:
        prompt_id: task ID
        client_id: client ID
    """
    if prompt_id not in task_manager.workflow_progress or prompt_id not in task_manager.callback_urls:
        return

    current_time = time.time()

    workflow_percent = task_manager.workflow_progress[prompt_id]["percent"]

    # Update last sent time
    task_manager.progress_throttle[prompt_id] = current_time

    # Get progress details
    current_node = task_manager.workflow_progress[prompt_id]["current_node"]
    completed_nodes = task_manager.workflow_nodes.get(prompt_id, {}).get("completed", 0)
    total_nodes = task_manager.workflow_nodes.get(prompt_id, {}).get("total", 100)
    execution_order = task_manager.workflow_progress.get(prompt_id, {}).get("execution_order", [])
    node_progress = task_manager.workflow_progress.get(prompt_id, {}).get("node_progress", {})
    active_node = task_manager.workflow_nodes.get(prompt_id, {}).get("active_node")

    callback_event = "task_workflow_progress"
    callback_data = {
        "prompt_id": prompt_id,
        "client_id": client_id,
        "status": "running",
        "progress": workflow_percent,
        "progress_details": {
            "percent": workflow_percent,
            "current_node": current_node,
            "active_node": active_node,
            "completed_nodes": completed_nodes,
            "total_nodes": total_nodes,
            "execution_order": execution_order,
            "node_progress": node_progress  # progress information of each node
        },
        "message": f"Workflow total progress: {workflow_percent}%，executed: {completed_nodes}/{total_nodes} nodes，current node: {current_node}",
        "timestamp": int(time.time())
    }

    ws_manager.ws_event_queue.put((prompt_id, "callback", (callback_event, callback_data)))
    if check_verbose_logging():
        logger.info(f"[comfy-deploy] Send callback for task {prompt_id}: {callback_data}")

def safe_handle_progress(data: dict) -> None:
    """
    Safe handle progress event, add throttling control
    
    Parameters:
        data: progress event data
    """
    if not check_event_handling():
        return

    try:
        prompt_id = data.get("prompt_id")

        if not prompt_id:
            client_id = data.get("client_id")
            if client_id and client_id in task_manager.client_prompts:
                prompt_id = task_manager.client_prompts[client_id]

        if not prompt_id:
            return

        if not task_manager.is_api_task(prompt_id):
            return

        # Get total progress
        workflow_percent = 0
        if prompt_id in task_manager.workflow_progress:
            workflow_percent = task_manager.workflow_progress[prompt_id]["percent"]

        # if the interval is too short, skip this update
        current_time = time.time()
        last_update_time = task_manager.progress_throttle.get(prompt_id, 0)

        # if the interval is long enough, handle the progress event and update the time
        if current_time - last_update_time >= config.PROGRESS_THROTTLE_INTERVAL:
            task_manager.progress_throttle[prompt_id] = current_time

            ws_manager.ws_event_queue.put((prompt_id, "task_workflow_progress", {
                "prompt_id": prompt_id,
                "status": "running",
                "progress": workflow_percent,
                "progress_details": task_manager.workflow_progress.get(prompt_id, {})
            }))
            
            if check_verbose_logging():
                logger.info(f"[comfy-deploy] Add progress event of task {prompt_id} to WebSocket queue, progress: {workflow_percent}%")

        # Clean up throttling record of completed tasks
        for pid in list(task_manager.progress_throttle.keys()):
            if pid not in task_manager.workflow_progress:
                task_manager.progress_throttle.pop(pid, None)

    except Exception as e:
        logger.error(f"[Safe handle] Error handling progress event: {str(e)}")
        import traceback
        logger.error(f"[Safe handle] Error details: {traceback.format_exc()}")


# ========================= Event intercept and rewrite =========================
# Intercept events by modifying the send_sync method of PromptServer
original_send_sync = server.PromptServer.send_sync


def custom_send_sync(self, event, data, sid=None):
    """
    Modified event sending method, intercept all events
    
    Parameters:
        event_name: event name
        data: event data
        sid: session ID
        
    Returns:
        Original method's return value
    """
    event_name = event
    # Call original method, ensure original event processing is not affected
    result = original_send_sync(self, event_name, data, sid)

    if not check_event_handling():
        return result

    try:
        str_event_name = str(event_name) if not isinstance(event_name, str) else event_name

        if "crystools.monitor" not in str_event_name:
            if check_verbose_logging():
                logger.info(f"[PromptServer] Send event: {str_event_name}, data: {str(data)[:300]}...")

            if any(keyword in str_event_name for keyword in ["execution", "prompt", "executed", "executing"]):
                if check_verbose_logging():
                    logger.warning(f"[Important event] Capture execution related event: {str_event_name}, full data: {str(data)}")

        event_handler.handle_event(str_event_name, data)
    except Exception as e:
        logger.error(f"[Event handling] Error handling event {event_name}: {str(e)}")

    return result


# Replace original method
server.PromptServer.send_sync = custom_send_sync


# ========================= Task execution and management =========================
def random_seed():
    return random.randint(0, 1125899906842624)

def apply_random_seed_to_workflow(workflow_api):
    for node_id, _ in workflow_api.items():
        if "inputs" in workflow_api[node_id]:
            if "seed" in workflow_api[node_id]["inputs"]:
                if isinstance(workflow_api[node_id]["inputs"]["seed"], list):
                    continue
                workflow_api[node_id]["inputs"]['seed'] = random_seed()
                key = node_id
                if "noise_seed" in workflow_api[key]["inputs"]:
                    if isinstance(workflow_api[key]["inputs"]["noise_seed"], list):
                        continue
                    if workflow_api[key]["class_type"] == "RandomNoise":
                        workflow_api[key]["inputs"]["noise_seed"] = random_seed()
                        logger.info(
                            f"Applied random noise_seed {workflow_api[key]['inputs']['noise_seed']} to RandomNoise"
                        )
                        continue
                    if workflow_api[key]["class_type"] == "KSamplerAdvanced":
                        workflow_api[key]["inputs"]["noise_seed"] = random_seed()
                        logger.info(
                            f"Applied random noise_seed {workflow_api[key]['inputs']['noise_seed']} to KSamplerAdvanced"
                        )
                        continue
                    if workflow_api[key]["class_type"] == "SamplerCustom":
                        workflow_api[key]["inputs"]["noise_seed"] = random_seed()
                        logger.info(
                            f"Applied random noise_seed {workflow_api[key]['inputs']['noise_seed']} to SamplerCustom"
                        )
                        continue
                    if workflow_api[key]["class_type"] == "XlabsSampler":
                        workflow_api[key]["inputs"]["noise_seed"] = random_seed()
                        logger.info(
                            f"Applied random noise_seed {workflow_api[key]['inputs']['noise_seed']} to XlabsSampler"
                        )
                        continue


async def execute_prompt(prompt: dict, client_id: str = None, pre_prompt_id: str = None) -> str:
    """
    Execute ComfyUI workflow task
    
    Parameters:
        prompt: ComfyUI workflow JSON
        client_id: optional client ID
        pre_prompt_id: optional preset prompt_id, if provided, use this ID instead of generating a new one
        
    Returns:
        Task ID
    """
    prompt_server = server.PromptServer.instance

    prompt_id = pre_prompt_id or str(uuid.uuid4())

    if not client_id:
        client_id = f"comfy-deploy-client-{prompt_id[:8]}"
        logger.info(f"[comfy-deploy] No client_id provided, generate new: {client_id}")

    partial_execution_targets = None
    if "partial_execution_targets" in prompt:
        partial_execution_targets = prompt["partial_execution_targets"]

    # Apply random seed
    apply_random_seed_to_workflow(prompt)

    # Validate task
    valid = await execution.validate_prompt(prompt_id, prompt, partial_execution_targets)

    if not valid[0]:
        logger.error(f"[comfy-deploy] Task validation failed: {valid[1]}")
        return None

    extra_data = {
        "client_id": client_id,
        "prompt_id": prompt_id
    }
    # ComfyUI v0.3.67 and above add sensitive data field
    sensitive_data = {}
    #logger.info(f"[comfy-deploy] Set client_id for task {prompt_id}: {client_id}")

    # Get output nodes
    outputs_to_execute = valid[2]

    # Submit task to queue
    number = prompt_server.number
    prompt_server.number += 1

    prompt_server.prompt_queue.put(
        (number, prompt_id, prompt, extra_data, outputs_to_execute, sensitive_data)
    )

    # Mark task as API created task
    task_manager.api_created_tasks.add(prompt_id)
    
    # Save client_id and prompt_id mapping
    task_manager.client_prompts[client_id] = prompt_id
    # logger.info(f"[comfy-deploy] Save client_id mapping: {client_id} -> {prompt_id}")

    return prompt_id


def get_task_details(prompt_id: str) -> dict:
    """
    Get task details
    
    Parameters:
        prompt_id: Task ID
        
    Returns:
        Task details dictionary
    """
    prompt_server = server.PromptServer.instance
    history = prompt_server.prompt_queue.get_history(prompt_id)
    
    if not history or prompt_id not in history:
        queue_info = prompt_server.prompt_queue.get_current_queue()
        current_tasks = queue_info[0]
        queued_tasks = queue_info[1]
        
        for task in current_tasks:
            if task[1] == prompt_id:
                return {
                    "prompt_id": prompt_id,
                    "status": "running",
                    "progress": task_manager.workflow_progress.get(prompt_id, {}).get("percent", 0),
                    "current_node": task_manager.workflow_progress.get(prompt_id, {}).get("current_node")
                }
                
        for i, task in enumerate(queued_tasks):
            if task[1] == prompt_id:
                return {
                    "prompt_id": prompt_id,
                    "status": "queued",
                    "position": i + 1
                }
                
        return None
    
    history_data = history.get(prompt_id, {})
    status_info = history_data.get('status', {})
    outputs = history_data.get('outputs', {})
    
    result = {
        "prompt_id": prompt_id,
        "status": status_info.get('status_str', 'unknown'),
        "completed": status_info.get('completed', False),
        "has_output": len(outputs) > 0,
        "outputs": outputs
    }
    
    if status_info.get('completed', False) and not status_info.get('error', False):
        result["raw_outputs"] = outputs
    
    return result


def get_prompt_history() -> dict:
    prompt_server = server.PromptServer.instance
    try:
        # Try to get all history using no-parameter method
        return prompt_server.prompt_queue.get_history()
    except TypeError:
        try:
            all_history = {}
            for prompt_id in task_manager.callback_urls.keys():
                history = prompt_server.prompt_queue.get_history(prompt_id)
                if history and prompt_id in history:
                    all_history[prompt_id] = history[prompt_id]
            return all_history
        except Exception as e:
            logger.error(f"[History query] Failed to get history: {str(e)}")
            return {}



# ========================= API endpoints and routes =========================
@server.PromptServer.instance.routes.get("/api/v1/toggle_event_listener")
async def toggle_event_listener(request):
    """API endpoints for enabling or disabling event listener"""
    enable = request.query.get("enable", None)

    if enable is not None:
        if enable.lower() == "true":
            config.ENABLE_CUSTOM_EVENT_HANDLING = True
            logger.info("[comfy-deploy] Event listener enabled")
        elif enable.lower() == "false":
            config.ENABLE_CUSTOM_EVENT_HANDLING = False
            logger.info("[comfy-deploy] Event listener disabled")

    return web.json_response({
        "event_listener_enabled": check_event_handling()
    })


@server.PromptServer.instance.routes.get("/api/v1/toggle_verbose_logging")
async def toggle_verbose_logging(request):
    """API endpoints for enabling or disabling verbose logging"""
    enable = request.query.get("enable", None)

    if enable is not None:
        if enable.lower() == "true":
            config.ENABLE_VERBOSE_LOGGING = True
            logger.info("[comfy-deploy] Verbose logging enabled")
        elif enable.lower() == "false":
            config.ENABLE_VERBOSE_LOGGING = False
            logger.info("[comfy-deploy] Verbose logging disabled")

    return web.json_response({
        "verbose_logging_enabled": check_verbose_logging()
    })


@server.PromptServer.instance.routes.post("/api/v1/execute")
async def api_execute_prompt(request):
    """API endpoints for submitting task execution"""
    try:
        json_data = await request.json()
        prompt = json_data.get("prompt")
        callback_url = json_data.get("callback_url")

        pre_prompt_id = json_data.get("task_id")

        client_id = json_data.get("client_id") or f"comfy-deploy-{int(time.time())}"

        if not prompt:
            return web.json_response({"error": "No workflow data provided"}, status=400)

        prompt_id = await execute_prompt(prompt, client_id=client_id, pre_prompt_id=pre_prompt_id)

        if not prompt_id:
            return web.json_response({"error": "Task validation failed"}, status=400)

        # If client_id is machine ID, add task to machine associated task set
        if client_id in ws_manager.machine_listeners or client_id in ws_manager.machine_prompts:
            ws_manager.machine_prompts[client_id].add(prompt_id)
            logger.info(f"[comfy-deploy] Add task {prompt_id} to machine {client_id}")

            if client_id in ws_manager.machine_listeners and not ws_manager.machine_listeners[client_id].closed:
                asyncio.create_task(ws_manager.machine_listeners[client_id].send_json({
                    "event": "task_created",
                    "data": {
                        "prompt_id": prompt_id,
                        "client_id": client_id,
                        "status": "created",
                        "message": "Task created",
                        "timestamp": int(time.time())
                    }
                }))
                logger.info(f"[comfy-deploy] Send task created notification to machine {client_id}")

        if callback_url:
            task_manager.callback_urls[prompt_id] = callback_url
            logger.info(f"[comfy-deploy] Set callback URL for task {prompt_id}: {callback_url}")

        ws_manager.ws_event_queue.put((prompt_id, "callback", ("task_queued", {
            "prompt_id": prompt_id,
            "client_id": client_id,
            "status": "queued",
            "message": "Task queued",
            "timestamp": int(time.time())
        })))

        return web.json_response({"prompt_id": prompt_id, "client_id": client_id, "status": "submitted"})

    except Exception as e:
        logger.error(f"[comfy-deploy] Submit task failed: {str(e)}")
        import traceback
        logger.error(f"Error details: {traceback.format_exc()}")
        return web.json_response({"error": str(e)}, status=500)


@server.PromptServer.instance.routes.get("/api/v1/status/{prompt_id}")
async def api_get_prompt_status(request):
    """API endpoints for querying task status"""
    try:
        prompt_id = request.match_info.get("prompt_id", "")
        if not prompt_id:
            return web.json_response({"error": "No task ID provided"}, status=400)

        task_details = get_task_details(prompt_id)
        
        if not task_details:
            return web.json_response({"error": "Task not found"}, status=404)
            
        return web.json_response(task_details)

    except Exception as e:
        logger.error(f"[comfy-deploy] Query task status failed: {str(e)}")
        import traceback
        logger.error(f"Error details: {traceback.format_exc()}")
        return web.json_response({"error": str(e)}, status=500)


@server.PromptServer.instance.routes.get("/api/v1/output/{prompt_id}/{node_id}")
async def api_get_output(request):
    """API endpoints for getting task specific node output"""
    try:
        prompt_id = request.match_info.get("prompt_id", "")
        node_id = request.match_info.get("node_id", "")

        if not prompt_id or not node_id:
            return web.json_response({"error": "No task ID or node ID provided"}, status=400)

        task_details = get_task_details(prompt_id)
        
        if not task_details:
            return web.json_response({"error": "Task not found"}, status=404)
            
        outputs = task_details.get('outputs', {})
        
        if node_id not in outputs:
            return web.json_response({"error": "Node output not found"}, status=404)

        node_output = outputs.get(node_id, {})

        return web.json_response({
            "prompt_id": prompt_id,
            "node_id": node_id,
            "output": node_output
        })

    except Exception as e:
        logger.error(f"[comfy-deploy] Get task output failed: {str(e)}")
        import traceback
        logger.error(f"Error details: {traceback.format_exc()}")
        return web.json_response({"error": str(e)}, status=500)


@server.PromptServer.instance.routes.get("/comfy-deploy/status")
async def get_hello(_):
    """Health check endpoint"""
    return web.json_response({
        "status": "ok",
        "timestamp": int(time.time())
    })


# ========================= WebSocket management =========================
@server.PromptServer.instance.routes.get("/api/v1/ws/machine/{machine_id}")
async def machine_websocket_handler(request):
    machine_id = request.match_info.get("machine_id", "")
    if not machine_id:
        return web.Response(status=400, text="No machine ID provided")

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    ws_manager.machine_listeners[machine_id] = ws

    if machine_id not in ws_manager.machine_prompts:
        ws_manager.machine_prompts[machine_id] = set()

    # logger.info(f"[comfy-deploy] WebSocket connection established for machine {machine_id}")

    await ws.send_json({
        "event": "connected",
        "data": {
            "machine_id": machine_id,
            "message": "WebSocket connection established",
            "timestamp": int(time.time())
        }
    })

    try:
        # Check if there are associated tasks for this machine
        active_tasks = []
        for client_id, prompt_id in task_manager.client_prompts.items():
            if client_id == machine_id:
                active_tasks.append(prompt_id)
                ws_manager.machine_prompts[machine_id].add(prompt_id)

        # if active_tasks:
        #     logger.info(f"[comfy-deploy] Machine {machine_id} has {len(active_tasks)} associated tasks")

        # Keep connection, process client messages
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                if msg.data == "close":
                    await ws.close()
                elif msg.data == "ping":
                    await ws.send_json({"event": "pong", "data": {"timestamp": time.time()}})

            elif msg.type == web.WSMsgType.ERROR:
                logger.error(f"WebSocket connection error: {ws.exception()}")

    except Exception as e:
        logger.error(f"Error processing machine {machine_id} WebSocket: {str(e)}")
        import traceback
        logger.error(f"Error details: {traceback.format_exc()}")
    finally:
        # Clean up when connection is closed
        if machine_id in ws_manager.machine_listeners and ws_manager.machine_listeners[machine_id] == ws:
            del ws_manager.machine_listeners[machine_id]
            # logger.info(f"[comfy-deploy] WebSocket connection for machine {machine_id} closed")
    return ws


async def send_task_update(prompt_id, event_name, data):
    enhanced_data = data.copy() if isinstance(data, dict) else {"original_data": data}

    if event_name == "status" and isinstance(enhanced_data, dict):
        # Get progress information
        progress = task_manager.workflow_progress.get(prompt_id, {}).get('percent', 0)
        enhanced_data["progress"] = progress

        # Get current executing node
        current_node = task_manager.workflow_progress.get(prompt_id, {}).get("current_node")
        active_node = task_manager.workflow_nodes.get(prompt_id, {}).get("active_node")

        if "status" in enhanced_data:
            status = enhanced_data["status"]
            if status == "completed":
                enhanced_data["status"] = "success"
                enhanced_data["live_status"] = "completed"
            elif status in ["error", "failed"]:
                enhanced_data["status"] = "failed"
                enhanced_data["live_status"] = "failed"
            else:
                # Use current node's class_type as live_status
                node_id = current_node or active_node
                if node_id:
                    node_class_type = get_node_class_type(prompt_id, node_id)
                    enhanced_data["live_status"] = node_class_type
                    enhanced_data["node_id"] = node_id
                else:
                    enhanced_data["live_status"] = status

    if event_name == "progress" and isinstance(enhanced_data, dict):
        if "status" not in enhanced_data:
            enhanced_data["status"] = "running"

        # Get current executing node
        current_node = task_manager.workflow_progress.get(prompt_id, {}).get("current_node")
        active_node = task_manager.workflow_nodes.get(prompt_id, {}).get("active_node")

        # Use current node's class_type as live_status
        node_id = current_node or active_node
        if node_id:
            # Get node's type name
            node_class_type = get_node_class_type(prompt_id, node_id)
            enhanced_data["live_status"] = node_class_type
            # Keep node ID as extra information
            enhanced_data["node_id"] = node_id
        else:
            enhanced_data["live_status"] = "running"

        # Get workflow progress information
        progress = task_manager.workflow_progress.get(prompt_id, {}).get('percent', 0)
        enhanced_data["progress"] = progress

        enhanced_data["progress_details"] = task_manager.workflow_progress.get(prompt_id, {})

        # Add detailed node information
        if prompt_id in task_manager.workflow_nodes:
            enhanced_data["node_info"] = task_manager.workflow_nodes[prompt_id]

        # Get node type name for logging
        node_name = enhanced_data["live_status"]
        # logger.info(f"[comfy-deploy] WebSocket send task {prompt_id} progress event: {progress}%，current node: {node_name} (ID: {node_id})")

    if event_name == "task_workflow_progress":
        if "status" not in enhanced_data:
            enhanced_data["status"] = "running"

        current_node = task_manager.workflow_progress.get(prompt_id, {}).get("current_node")
        active_node = task_manager.workflow_nodes.get(prompt_id, {}).get("active_node")

        # Use current node's class_type as live_status
        node_id = current_node or active_node
        if node_id:
            node_class_type = get_node_class_type(prompt_id, node_id)
            enhanced_data["live_status"] = node_class_type
            enhanced_data["node_id"] = node_id
        else:
            enhanced_data["live_status"] = "running"

        if "progress" in enhanced_data:
            node_name = enhanced_data["live_status"]
            # logger.info(f"[comfy-deploy] WebSocket task {prompt_id} progress update: {enhanced_data['progress']}%，current node: {node_name} (ID: {node_id})")

            try:
                enhanced_data["progress"] = int(enhanced_data["progress"])
            except (ValueError, TypeError):
                enhanced_data["progress"] = 0
        elif "progress_details" in enhanced_data and "percent" in enhanced_data["progress_details"]:
            enhanced_data["progress"] = enhanced_data["progress_details"]["percent"]
            node_name = enhanced_data["live_status"]
            logger.info(f"[comfy-deploy] WebSocket task {prompt_id} progress update (from details): {enhanced_data['progress']}%，current node: {node_name} (ID: {node_id})")

    if event_name in ["execution_success", "task_success"]:
        enhanced_data["status"] = "success"
        enhanced_data["live_status"] = "completed"
        enhanced_data["progress"] = 100
        enhanced_data["completed"] = True

        try:
            prompt_server = server.PromptServer.instance
            history = prompt_server.prompt_queue.get_history(prompt_id)
            if history and prompt_id in history:
                history_data = history[prompt_id]
                outputs = history_data.get('outputs', {})

                # Extract output results
                result = {'images': [], 'videos': []}
                for output in outputs.values():
                    if output:
                        for k, v in output.items():
                            if 'images' in k:
                                result['images'].extend(v)
                            elif 'videos' in k or 'gifs' in k:
                                result['videos'].extend(v)

                enhanced_data["result"] = result
                enhanced_data["raw_outputs"] = outputs  # Add original outputs results
        except Exception as e:
            logger.error(f"Error getting task {prompt_id} results: {str(e)}")

    if event_name in ["execution_error", "task_failed"]:
        enhanced_data["status"] = "failed"
        enhanced_data["live_status"] = "failed"
        enhanced_data["completed"] = True

        if "error" not in enhanced_data and hasattr(data, "exception_message"):
            enhanced_data["error"] = data.exception_message

    # Record all event sending
    # logger.info(f"[comfy-deploy] WebSocket send task {prompt_id}, event: {event_name}, data type: {type(enhanced_data).__name__}")

    if prompt_id in ws_manager.task_listeners:
        closed_ws = []

        # Send to all connected clients
        message_sent = False
        for ws in ws_manager.task_listeners[prompt_id]:
            try:
                if not ws.closed:
                    message = {
                        "event": event_name,
                        "data": enhanced_data
                    }

                    await ws.send_json(message)
                    message_sent = True

                    logger.info(f"[comfy-deploy] WebSocket successfully sent {event_name} event to task {prompt_id}")
                else:
                    closed_ws.append(ws)
                    logger.warning(f"[comfy-deploy] WebSocket for task {prompt_id} is closed, cannot send")
            except Exception as e:
                logger.error(f"[comfy-deploy] Error sending update to WebSocket: {str(e)}")
                import traceback
                logger.error(f"Error details: {traceback.format_exc()}")
                closed_ws.append(ws)

        if message_sent:
            logger.info(f"[comfy-deploy] WebSocket successfully sent {event_name} event to {len(ws_manager.task_listeners[prompt_id]) - len(closed_ws)} clients of task {prompt_id}")
        else:
            logger.warning(f"[comfy-deploy] WebSocket warning, {event_name} event cannot be sent to any client of task {prompt_id}")

        for ws in closed_ws:
            if ws in ws_manager.task_listeners[prompt_id]:
                ws_manager.task_listeners[prompt_id].remove(ws)
                logger.info(f"[comfy-deploy] WebSocket cleanup, removed one closed connection of task {prompt_id}")

        if not ws_manager.task_listeners[prompt_id]:
            del ws_manager.task_listeners[prompt_id]
            logger.info(f"[comfy-deploy] WebSocket cleanup, task {prompt_id} has no active listeners, list deleted")

    # 2. Send update to associated machine WebSocket
    if event_name != "progress":
        await send_machine_updates_for_task(prompt_id, event_name, enhanced_data)


async def send_machine_updates_for_task(prompt_id, event_name, data):
    """Send task update to all associated machine WebSocket"""
    related_machines = []

    # 1. First try to find the corresponding machine ID (client_id) through client_prompts
    for machine_id, mapped_prompt_id in task_manager.client_prompts.items():
        if mapped_prompt_id == prompt_id:
            related_machines.append(machine_id)

            if machine_id in ws_manager.machine_prompts:
                ws_manager.machine_prompts[machine_id].add(prompt_id)
            else:
                ws_manager.machine_prompts[machine_id] = {prompt_id}

    # 2. Then check all known machine task lists
    for machine_id, prompt_ids in ws_manager.machine_prompts.items():
        if prompt_id in prompt_ids and machine_id not in related_machines:
            related_machines.append(machine_id)

    if not related_machines:
        return

    # logger.info(f"[comfy-deploy] Task {prompt_id} associated machines: {related_machines}")

    # Send update to all associated machines
    for machine_id in related_machines:
        await send_machine_task_update(machine_id, prompt_id, event_name, data)


async def send_machine_task_update(machine_id, prompt_id, event_name, data=None):
    if machine_id not in ws_manager.machine_listeners:
        # logger.warning(f"[comfy-deploy] Machine {machine_id} has no active WebSocket connection")
        return

    ws = ws_manager.machine_listeners[machine_id]
    if ws.closed:
        # logger.warning(f"[comfy-deploy] Machine {machine_id} WebSocket connection is closed")
        del ws_manager.machine_listeners[machine_id]
        return

    enhanced_data = data
    if enhanced_data is None:
        prompt_server = server.PromptServer.instance

        queue_info = prompt_server.prompt_queue.get_current_queue()
        current_tasks = queue_info[0]  # Current executing task
        queued_tasks = queue_info[1]   # Queued tasks

        is_running = False
        is_queued = False

        for task in current_tasks:
            if task[1] == prompt_id:
                is_running = True
                break

        if not is_running:
            for task in queued_tasks:
                if task[1] == prompt_id:
                    is_queued = True
                    break

        # Get task history and progress
        history = prompt_server.prompt_queue.get_history(prompt_id)
        history_data = history.get(prompt_id, {}) if history else {}
        progress_info = task_manager.workflow_progress.get(prompt_id, {})
        current_progress = progress_info.get('percent', 0)

        # Get current executing node
        current_node = progress_info.get("current_node")
        active_node = task_manager.workflow_nodes.get(prompt_id, {}).get("active_node")

        # Build status data
        enhanced_data = {
            "prompt_id": prompt_id,
            "client_id": machine_id,
            "status": "unknown",
            "progress": current_progress
        }

        if history_data:
            status_info = history_data.get('status', {})
            outputs = history_data.get('outputs', {})
            completed = status_info.get('completed', False)
            error = status_info.get('error', False)

            if completed:
                enhanced_data["status"] = "success" if not error else "failed"
                enhanced_data["live_status"] = "completed"
                enhanced_data["completed"] = True
                enhanced_data["progress"] = 100

                if not error and len(outputs) > 0:
                    result = {'images': [], 'videos': []}
                    for output in outputs.values():
                        if output:
                            for k, v in output.items():
                                if 'images' in k:
                                    result['images'].extend(v)
                                elif 'videos' in k or 'gifs' in k:
                                    result['videos'].extend(v)
                    enhanced_data["result"] = result
                    enhanced_data["raw_outputs"] = outputs

                if error:
                    enhanced_data["error"] = status_info.get('error_message', 'Unknown error')

            elif is_running:
                enhanced_data["status"] = "running"
                node_id = current_node or active_node
                if node_id:
                    node_class_type = get_node_class_type(prompt_id, node_id)
                    enhanced_data["live_status"] = node_class_type
                    enhanced_data["node_id"] = node_id
                else:
                    enhanced_data["live_status"] = "running"

                enhanced_data["completed"] = False
                enhanced_data["progress_details"] = progress_info

            elif is_queued:
                queue_position = 0
                for i, task in enumerate(queued_tasks):
                    if task[1] == prompt_id:
                        queue_position = i + 1
                        break

                enhanced_data["status"] = "queued"
                enhanced_data["live_status"] = "queued"
                enhanced_data["completed"] = False
                enhanced_data["progress"] = 0
                enhanced_data["position"] = queue_position
    else:
        if isinstance(enhanced_data, dict) and "status" in enhanced_data and "live_status" not in enhanced_data:
            current_node = task_manager.workflow_progress.get(prompt_id, {}).get("current_node")
            active_node = task_manager.workflow_nodes.get(prompt_id, {}).get("active_node")

            status = enhanced_data["status"]
            if status == "success":
                enhanced_data["live_status"] = "completed"
            elif status == "failed":
                enhanced_data["live_status"] = "failed"
            elif status == "running":
                node_id = current_node or active_node
                if node_id:
                    node_class_type = get_node_class_type(prompt_id, node_id)
                    enhanced_data["live_status"] = node_class_type
                    enhanced_data["node_id"] = node_id
                else:
                    enhanced_data["live_status"] = "running"
            else:
                enhanced_data["live_status"] = status

    try:
        message = {
            "event": event_name,
            "data": enhanced_data
        }

        await ws.send_json(message)
        # logger.info(f"[comfy-deploy] Sent {event_name} event to machine {machine_id} for task {prompt_id}")
        return True
    except Exception as e:
        logger.error(f"[comfy-deploy] Error sending update to machine {machine_id}: {str(e)}")
        return False


# ========================= Async task and callback processing =========================
@server.PromptServer.instance.app.on_startup.append
async def start_ws_queue_processor(_):
    """Start WebSocket event queue processor when server starts"""
    asyncio.create_task(process_ws_event_queue())


async def process_ws_event_queue():
    """Async task: process WebSocket events and callbacks, add detailed logging"""
    logger.info("[comfy-deploy] Start running WebSocket event queue processor")
    while True:
        try:
            if not ws_manager.ws_event_queue.empty():
                prompt_id, event_type, data = ws_manager.ws_event_queue.get()

                if event_type == "callback":
                    # Process callback notification
                    callback_event_name, callback_data = data
                    await send_callback(prompt_id, callback_event_name, callback_data)
                else:
                    # Process WebSocket notification
                    await send_task_update(prompt_id, event_type, data)

            # Check queue every 100ms
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"[comfy-deploy] Error processing event queue: {str(e)}")
            await asyncio.sleep(1)


async def send_callback(prompt_id, event_name, data):

    if not check_event_handling():
        return

    if prompt_id not in task_manager.callback_urls:
        logger.warning(f"[comfy-deploy] Task {prompt_id} has no callback URL configured")
        return

    callback_url = task_manager.callback_urls[prompt_id]

    try:
        callback_data = {
            "event": event_name,
            "data": data,
            "timestamp": int(time.time())
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                callback_url,
                json=callback_data,
                timeout=5.0
            )

            if response.status_code != 200:
                logger.warning(
                    f"[comfy-deploy] Send failed: {event_name} -> {callback_url}, "
                    f"Status code: {response.status_code}, Response: {response.text[:100]}"
                )

    except Exception as e:
        logger.error(f"[comfy-deploy] Error sending {event_name} event: {str(e)}")

    if event_name in ["task_success", "task_failed"]:
        task_manager.callback_urls.pop(prompt_id, None)
        if prompt_id in task_manager.api_created_tasks:
            task_manager.api_created_tasks.remove(prompt_id)


# ========================= Utility functions =========================
def get_node_class_type(prompt_id: str, node_id: str) -> str:
    """
    Get node type name from workflow definition
    
    Parameters:
        prompt_id: task ID
        node_id: node ID
        
    Returns:
        Node type name, if not found, return node ID
    """
    if prompt_id not in task_manager.workflow_nodes:
        return str(node_id)

    workflow_definition = task_manager.workflow_nodes[prompt_id].get("workflow_definition", {})

    if not workflow_definition or node_id not in workflow_definition:
        return str(node_id)

    node_info = workflow_definition.get(node_id, {})
    class_type = node_info.get("class_type", str(node_id))

    return class_type


# ========================= Event registration and initialization =========================
# Register ComfyUI event handler
event_handler.register_event("execution_start",
                             lambda data: handle_execution_events_with_ws_and_callback("execution_start", data))
event_handler.register_event("execution_cached",
                             lambda data: handle_execution_events_with_ws_and_callback("execution_cached", data))
event_handler.register_event("executing", lambda data: handle_execution_events_with_ws_and_callback("executing", data))
event_handler.register_event("executed", lambda data: handle_execution_events_with_ws_and_callback("executed", data))
event_handler.register_event("execution_error",
                             lambda data: handle_execution_events_with_ws_and_callback("execution_error", data))
event_handler.register_event("execution_success",
                             lambda data: handle_execution_events_with_ws_and_callback("execution_success", data))

# Register progress event handler
event_handler.register_event("progress", safe_handle_progress)


logger.info("[ComfyDeploy] custom routes initialization completed")
logger.info("Registered API endpoint: /api/v1/execute")
logger.info("Registered API endpoint: /api/v1/status/{prompt_id}")
logger.info("Registered API endpoint: /api/v1/output/{prompt_id}/{node_id}")
logger.info("Registered WebSocket endpoint: /api/v1/ws/task/{prompt_id}")
logger.info("Registered WebSocket endpoint: /api/v1/ws/machine/{machine_id}")
logger.info("Registered API endpoint: /api/v1/toggle_event_listener")
logger.info("Registered API endpoint: /api/v1/toggle_verbose_logging")
logger.info(f"Detailed logging status: {'Enabled' if check_verbose_logging() else 'Disabled'}")
logger.info(f"[ComfyDeploy] initialization completed, event listener status: {'Enabled' if check_event_handling() else 'Disabled'}")
