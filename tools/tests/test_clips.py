import numpy as np
import pytest

from helpers import quad
from uwmodels import clips, gltf


def creature():
    return quad(np.zeros((4, 4, 3), np.uint8), clips={"idle": [0, 0.125], "idle_combat": [0, 0.125, 0.25, 0.375]},
                joints=2)


def test_copy_motion_keeps_name_and_order():
    g = clips.copy_clip(creature(), "idle_combat", "idle")
    assert gltf.clip_names(g) == ["idle", "idle_combat"]
    a, b = g.json["animations"]
    assert [c["target"] for c in a["channels"]] == [c["target"] for c in b["channels"]]
    times = gltf.accessor(g, a["samplers"][0]["input"]).ravel()
    assert np.allclose(times, [0, 0.125, 0.25, 0.375])


def test_copy_is_independent_of_the_source():
    g = clips.copy_clip(creature(), "idle_combat", "idle")
    g.json["animations"][1]["samplers"][0]["interpolation"] = "STEP"
    assert g.json["animations"][0]["samplers"][0].get("interpolation") != "STEP"


def test_missing_clip_is_an_error():
    with pytest.raises(KeyError):
        clips.copy_clip(creature(), "walking", "idle")
