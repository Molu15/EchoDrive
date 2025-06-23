import carla
import time
import threading

import audio_manager
import rss_manager
import gesture_manager
from echolocation_game import EcholocationGame


def find_ego_vehicle(world):
    vehicles = world.get_actors().filter('vehicle.*')
    for vehicle in vehicles:
        if vehicle.attributes.get('role_name') == 'hero':
            return vehicle
    return None

def wait_for_ego_vehicle(world, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        ego = find_ego_vehicle(world)
        if ego:
            return ego
        time.sleep(0.5)
    return None

def main(score_tracker=None, takeover_manager=None, stop_event=None, trigger_manager=None, game_ready_event=None):
    print ("[Debug] main init")
    client = carla.Client("localhost", 2000)
    client.set_timeout(10.0)
    world = client.get_world()

    # Init managers
    rss = rss_manager.RSSManager(world)
    gesture = gesture_manager.GestureManager()

    if score_tracker is None:
        from score_tracker import ScoreTracker
        score_tracker = ScoreTracker()
    if takeover_manager is None:
        from takeover_manager import TakeoverManager
        takeover_manager = TakeoverManager()
    if trigger_manager is None:
        from trigger_manager import TriggerManager
        trigger_manager = TriggerManager()

    print ("[Debug] main ready")

    ego_vehicle = wait_for_ego_vehicle(world)
    if ego_vehicle:
        if game_ready_event:    
            game_ready_event.set()
        print(f"[Main] Ego vehicle found: ID {ego_vehicle.id}")
    else:
        print("[Main] Ego vehicle with role_name='hero' not found after waiting.")
        return

    print ("[Debug] main game init")
    game = EcholocationGame(
        carla_world=world,
        ego_vehicle=ego_vehicle,
        rss_manager=rss,
        audio_manager=audio_manager,
        gesture_manager=gesture,
        score_tracker=score_tracker,
        takeover_manager=takeover_manager,
        trigger_manager=trigger_manager
    )
    takeover_manager.set_game(game)
    print ("[Debug] main game ready")
    try:
        print ("[Debug] main game threading")
        audio_manager.play_music()
        #game_thread = threading.Thread(target=game.run, daemon=True)
        game_thread = threading.Thread(target=game.run, kwargs={"stop_event": stop_event}, daemon=True)
        game_thread.start()

        while game_thread.is_alive():
            if stop_event and stop_event.is_set():
                print("[Main] Stop event received, stopping game...")
                game.stop()
                break
            time.sleep(0.1)

        game_thread.join(timeout=5)
        if game_thread.is_alive():
            print("[Main] Warning: Game thread did not shut down cleanly.")
        else:
            print("[Main] Game thread joined successfully.")

    except KeyboardInterrupt:
        print("[Main] Game interrupted by user.")
        game.stop()
        game_main_thread.join(timeout=5)
    finally:
        print("[Main] Shutting down begin....")
        audio_manager.shutdown_audio()
        print("[Main] Shutting down 1")
        gesture.shutdown()
        print("[Main] Shutting down 2")
        game.closeCSV()
        print("[Main] Shutting down 3")
        score_tracker.closeCSV()
        print("[Main] Shutting down 4")
        if takeover_manager.active:
            takeover_manager.shutdown()
            print ("[Main] TOR shutdown")

        print ("[Main].. and finished")

if __name__ == "__main__":
    main()
