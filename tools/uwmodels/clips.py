"""Edits a model's animation clips.

copy_clip gives one clip the motion of another in the same model: the same channels and keyframes, sharing the
source's keyframe data, under the target clip's own name and place in the list. Most creatures' idle clips came
from the PlayStation version as one held pose, where the game's standing sprites animate; their idle takes the
motion of their idle_combat clip, which loops the same way.
"""
import copy


def copy_clip(glb, src: str, dst: str):
    anims = glb.json.get("animations", [])
    by = {a.get("name"): a for a in anims}
    if src not in by or dst not in by:
        raise KeyError(f"no clip named {src if src not in by else dst}")
    new = copy.deepcopy(by[src])
    new["name"] = dst
    anims[anims.index(by[dst])] = new
    return glb
