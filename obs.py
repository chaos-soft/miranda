import os

import obspython as obs

i: int = 1
iterations: int = 0
PATH: str = '/tmp/miranda'
total: int = 0


def main():
    global i
    global total
    if not os.path.isfile(PATH):
        return None
    with open(PATH, 'r') as f:
        total_new = int(f.read())
        if total == total_new and i == iterations:
            show(False)
        elif total != total_new:
            i = 0
            show(True)
            total = total_new
    i += 1


def reset():
    global i
    i = 1
    obs.timer_remove(main)
    obs.timer_add(main, 5 * 1000)
    show(True)


def script_defaults(settings):
    obs.obs_data_set_default_int(settings, 'iterations', 12)


def script_load(settings):
    reset()


def script_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_int_slider(props, 'iterations', 'Итерации', 1, 12, 1)
    return props


def script_update(settings):
    global iterations
    iterations = obs.obs_data_get_int(settings, 'iterations')
    reset()


def show(value=True):
    scene = obs.obs_scene_from_source(obs.obs_frontend_get_current_scene())
    source = obs.obs_scene_find_source(scene, 'miranda')
    obs.obs_sceneitem_set_visible(source, value)
