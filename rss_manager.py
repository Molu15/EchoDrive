# rss_manager.py

import carla
import math


class RSSManager:
    def __init__(self, carla_world):
        print ("[Debug] rss init")
        self.world = carla_world
        print ("[Debug] rss ready")

    def get_nearest_entity(self, ego_vehicle):
        actors = self.world.get_actors()
        relevant_types = ['vehicle', 'walker.pedestrian']  # bicycle runs under vehicle

        ego_location = ego_vehicle.get_transform().location
        nearest_entity = None
        min_distance = float('inf')

        for actor in actors:
            if actor.id == ego_vehicle.id:
                continue

            if not any(t in actor.type_id for t in relevant_types):
                continue

            actor_location = actor.get_transform().location
            distance = self._compute_distance(ego_location, actor_location)


            if distance < min_distance:
                min_distance = distance
                nearest_entity = actor

        if nearest_entity:
            print(f"[RSS] Nearest entity: {nearest_entity.type_id} (id={nearest_entity.id}) at {nearest_entity.get_transform().location}, distance: {min_distance:.2f}")
        else:
            print("[RSS] No relevant entity found.")

        direction_vector = actor_location - ego_location


        return nearest_entity


    def _compute_distance(self, loc1, loc2):
        dx = loc1.x - loc2.x
        dy = loc1.y - loc2.y
        dz = loc1.z - loc2.z
        return math.sqrt(dx*dx + dy*dy + dz*dz)
