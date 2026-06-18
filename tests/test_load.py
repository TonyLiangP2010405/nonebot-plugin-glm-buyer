import nonebot


def test_plugin_load():
    nonebot.init()
    plugin = nonebot.load_plugin("nonebot_plugin_glm_buyer")
    assert plugin is not None
