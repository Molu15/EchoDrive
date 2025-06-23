import subprocess
import time
import os
import sys
import carla
from score_tracker import ScoreTracker
from takeover_manager import TakeoverManager
from trigger_manager import TriggerManager
from base_game import BaseManager
import main_game
import threading
import signal
import pygame


# === SET EXPERIMENT CONTEXT EARLY 
from csv_logger import set_experiment_context
experiment_id = input("[Start] Enter Participant ID (e.g., name of participant or P01...): ").strip() or "default"
print(f"[Start] You are now running Experiment: {experiment_id}")

while True:
    scenario_type = input("[Start] Enter Scenario (BASE | ECHO | TRIAL): ").strip().upper()
    #made this if else shorter
    if scenario_type in ("BASE", "ECHO", "TRIAL"):
        print(f"[Start] You are now running Experiment: {experiment_id} ({scenario_type})")
        set_experiment_context(experiment_id, scenario_type)
        echoDrive = scenario_type in ("ECHO", "TRIAL")
        break
    else:
        print("[Start] Invalid input. Please enter 'BASE', 'ECHO' or 'TRIAL'. Try again.")

#====================================
    

stop_event = threading.Event()
game_ready_event = threading.Event()

def signal_handler(sig, frame):
        print("[Start] Signal received, cleaning up...")
        stop_event.set()
        #pygame.quit()
        #sys.exit(0)

# === KONFIGURATION ===
CARLA_ROOT = os.path.abspath(os.path.dirname(__file__))
EXAMPLES_PATH = os.path.join(CARLA_ROOT, "PythonAPI", "examples")
UTIL_PATH = os.path.join(CARLA_ROOT, "PythonAPI", "util")
RHYTHM_GAME_PATH = os.path.join(CARLA_ROOT, "RhythmGame")
CARLA_API_PATH = os.path.join(CARLA_ROOT, "carla")
if CARLA_API_PATH not in sys.path:
        sys.path.append(CARLA_API_PATH)


# === FUNCTION: Wait for Carla Simulator ===
def wait_for_carla(timeout=40):
    print("[Start] Waiting for Carla to be ready...")
    client = carla.Client("localhost", 2000)
    client.set_timeout(2.0)

    start = time.time()
    try:
        while time.time() - start < timeout:
            try:
                client.get_world()
                print("[Start] Carla is ready.")
                return True
            except RuntimeError:
                print("[Start] Still waiting for Carla simulator...")
                time.sleep(2)
    except KeyboardInterrupt:
        print("[Start] Interrupted while waiting for Carla.")
        return False

    print("[Start] Carla simulator did not become ready in time.")
    print("[Start] Check for other processes: netstat -aon | findstr :2000")
    print("[Start] Kill blocking processes: taskkill /PID <number> /F")
    return False
  

# === FUNCTION: Wait for Carla World to Stabilize ===
def wait_for_world_ready(timeout=60):
    print("[Start] Waiting for Carla world to stabilize...")
    client = carla.Client("localhost", 2000)
    client.set_timeout(20.0)
    start = time.time()
    while time.time() - start < timeout:
        try:
            world = client.get_world()
            if world.get_map() is not None:
                print("[Start] Carla world is ready.")
                return True
        except:
            pass
        print("[Start] Still waiting for world to be ready...")
        time.sleep(2)
    print("[Start] Carla world did not become ready in time.")
    print("[Start] Check for other processes: netstat -aon | findstr :2000")
    print("[Start] Kill blocking porcesses: taskkill /PID <number open the right> /F")
    return False

def wait_for_ego_vehicle(role_name='hero', timeout=30):
    print("[Start] Waiting for ego vehicle to be spawned...")
    client = carla.Client('localhost', 2000)
    client.set_timeout(20.0)
    start = time.time()

    while time.time() - start < timeout:
        world = client.get_world()
        vehicles = world.get_actors().filter('vehicle.*')
        for v in vehicles:
            if v.attributes.get('role_name') == role_name:
                print("[Start] Ego vehicle is ready.")
                return True
        time.sleep(1)

    print("[Start] Ego vehicle was not found in time.")
    return False

def terminal_input_listener(takeover_manager):
        while True:
            inp = sys.stdin.readline()
            if takeover_manager.takeover_requested and takeover_manager.reaction_time is None and not takeover_manager.finished:
                takeover_manager.record_reaction()

# === MAIN STARTUP SEQUENCE ===
try:
    time.sleep(5)

    # Scenario Runner ---------------------------------------------------------------------------------------------------------------
    print("[Start] Starting scenario...")
    if echoDrive:
        if scenario_type == "ECHO":
            process = subprocess.Popen(
                [
                    "python", "scenario_runner.py",
                    "--route", "./route_20.xml", "./srunner/data/no_scenarios.json",
                    "--agent", "./srunner/autoagents/npc_agent.py",
                    "--timeout", "30.0" #increased timeout for scenario runner
                ],
                cwd=CARLA_ROOT,
            )
        else:
            process = subprocess.Popen(
                [
                    "python", "scenario_runner.py",
                    "--route", "./route_tutorial.xml", "./srunner/data/no_scenarios.json",
                    "--agent", "./srunner/autoagents/npc_agent.py",
                    "--timeout", "30.0" #increased timeout for scenario runner
                ],
                cwd=CARLA_ROOT,
            )
    else:
        process = subprocess.Popen(
            [
                "python", "scenario_runner.py",
                "--route", "./route_29.xml", "./srunner/data/no_scenarios.json",
                "--agent", "./srunner/autoagents/npc_agent.py",
                "--timeout", "30.0" #increased timeout for scenario runner
            ],
            cwd=CARLA_ROOT,
        )
        
    #time.sleep(7.0)

    # wait for world & ego ready ---------------------------------------------------------------------------------------------------------------------
    if not wait_for_world_ready(timeout=60):
        print("[Start] Exiting because Carla world did not become ready.")
        stop_event.set()
        sys.exit(1)

    if echoDrive:
        wait_for_ego_vehicle(role_name="hero")

    # Score Tracker & Trigger Manager ---------------------------------------------------------------------------------------------------------------------------------
    if echoDrive:
        score_tracker = ScoreTracker()
        trigger_manager = TriggerManager(keys=('space','enter'))
    else:
        score_tracker = None
        trigger_manager = TriggerManager(keys=('enter'))
    # Takeover Manager ------------------------------------------------------------------------------------------------------------------------------
    if echoDrive:
        if scenario_type == "ECHO":
           # my_delays = [60.0, 530.0, 900.0]  # 15min
           #my_delays = [120.0, 287.0, 321.0, 410.0, 422.2, 510.0,  600.0] # 10min
           my_delays = [77.0, 119.0, 194.0, 321.0, 410.0, 556.0, 600.0] # NEW for scenario adjusted 10min 
           # my_delays = [30.0, 60.0] # test 1min
        else:
            my_delays = [180.0]
    else:
        # my_delays = [90.0, 610.0, 900.0] # 15min
        my_delays = [90.0, 120.0, 217.0, 320.0, 430.0, 504.0, 600.0] # 10min
        # my_delays = [30.0, 60.0] # test 1min

    takeover_manager = TakeoverManager(trigger_delays=my_delays, stop_event=stop_event, trigger_manager=trigger_manager)

    time.sleep(1.0)

    takeover_thread = threading.Thread(target=takeover_manager.run)
    takeover_manager.thread = takeover_thread
    takeover_thread.start()

    time.sleep(1.0)

    # Signal Handler ---------------------------------------------------------------------------------------------------------------
    signal.signal(signal.SIGINT, signal_handler)

    # Manual Control ---------------------------------------------------------------------------------------------------------------
    print("[Start] Starting manual control...")

    import scenario_runner_manual_control
    import argparse

    time.sleep(2.0)
    
    argparser = argparse.ArgumentParser(
        description='CARLA Manual Control Client')
    argparser.add_argument(
        '-v', '--verbose',
        action='store_true',
        dest='debug',
        help='print debug information')
    argparser.add_argument(
        '--host',
        metavar='H',
        default='127.0.0.1',
        help='IP of the host server (default: 127.0.0.1)')
    argparser.add_argument(
        '-p', '--port',
        metavar='P',
        default=2000,
        type=int,
        help='TCP port to listen to (default: 2000)')
    argparser.add_argument(
        '-a', '--autopilot',
        action='store_true',
        help='enable autopilot. This does not autocomplete the scenario')
    argparser.add_argument(
        '--rolename',
        metavar='NAME',
        default='hero',
        help='role name of ego vehicle to control (default: "hero")')
    argparser.add_argument(
        '--res',
        metavar='WIDTHxHEIGHT',
        default='1280x720',
        help='window resolution (default: 1280x720)')
    argparser.add_argument(
        '--keep_ego_vehicle',
        action='store_true',
        help='do not destroy ego vehicle on exit')
    argparser.add_argument(
        '--fullscreen', 
        action='store_true', 
        help='run in fullscreen mode')


    args = argparser.parse_args(['--autopilot', '--fullscreen'])
    
    
    manual_thread = threading.Thread(target=scenario_runner_manual_control.run_manual_control, args=(score_tracker, takeover_manager, args, stop_event, game_ready_event))
    manual_thread.daemon = True
    manual_thread.start()

    time.sleep(0.1)

    # Rendering OFF ---------------------------------------------------------------------------------------------------------------
    print ("[Start] Turn off rendering")
    subprocess.Popen(["python", "config.py", "--no-rendering"], cwd=UTIL_PATH)

    #time.sleep(0.1)

    # Start Game Logic ---------------------------------------------------------------------------------------------------------------
    if echoDrive:
        print("[Start] Starting Echolocation...")
        game_thread = threading.Thread(
            target=main_game.main,
            args=(score_tracker, takeover_manager, stop_event, trigger_manager, game_ready_event),
            daemon=True
        )
        game_thread.start()

        #main_game.main(score_tracker, takeover_manager, stop_event, trigger_manager, game_ready_event)
    else:
        base_manager = BaseManager(takeover_manager, stop_event, game_ready_event)
        base_thread = threading.Thread(target=base_manager.run, daemon=True)
        base_thread.start()
        takeover_manager.set_game(base_manager)


    print(f"[Start] Waiting loop start. stop_event set? {stop_event.is_set()}")
    while not stop_event.is_set():
        time.sleep(0.1)
    #print("[Start] Exited wait loop.")

except KeyboardInterrupt:
    print("[Start] Interrupted by user.")
    stop_event.set()

finally:
    print("[Start] Setting stop event for shutdown.")
    stop_event.set()

    try:
        if 'game_main_thread' in locals():
            print("[Start] Waiting for game main thread to join...")
            game_main_thread.join(timeout=5)
            print("[Start] Game main thread joined.")

        if 'manual_thread' in locals():
            print("[Start] Waiting for manual thread to join...")
            manual_thread.join(timeout=5)
            print("[Start] Manual thread joined.")

        if 'takeover_manager' in locals():
            print("[Start] Shutting down takeover manager...")
            takeover_manager.shutdown()

        if 'takeover_thread' in locals():
            print("[Start] Waiting for takeover thread to join...")
            takeover_thread.join(timeout=5)
            print("[Start] Takeover thread joined.")

        if 'base_manager' in locals():
            print("[Start] Shutting down base manager...")
            base_manager.shutdown()

        if 'base_thread' in locals():
            print("[Start] Waiting for base thread to join...")
            base_thread.join(timeout=5)
            print("[Start] Base thread joined.")

        if 'process' in locals() and process:
            print("[Start] Terminating scenario runner...")
            process.terminate()
            try:
                process.wait(timeout=5)
                print("[Start] Scenario runner terminated.")
            except subprocess.TimeoutExpired:
                print("[Start] Scenario runner did not terminate in time, killing...")
                process.kill()
                process.wait()
    except Exception as e:
        print(f"[Start] Error during shutdown: {e}")

    pygame.quit()
    print("[Start] Shutdown complete.")
    print("[Start] See you later alligator")