import numpy as np

from uwmodels import thumbs, uwvx
from uwmodels.uwvc import write_uwvc


def one_voxel(tmp_path):
    m = uwvx.Model(0.01, (0, 0, 0), {"still": [np.array([[0, 0, 0, 5]], np.uint8)]})
    p = tmp_path / "a.uwvc"
    write_uwvc(m, [{5: (200, 200, 200)}], p)
    return np.asarray(thumbs.render(p, px=128))


def test_single_voxel_is_centred(tmp_path):
    img = one_voxel(tmp_path)
    ys, xs = np.nonzero(img[..., 3] > 0)
    assert abs(xs.mean() - 64) < 3 and abs(ys.mean() - 64) < 3
    assert xs.max() - xs.min() > 80   # fitted with a margin, not drawn tiny


def test_background_transparent(tmp_path):
    img = one_voxel(tmp_path)
    for y, x in [(0, 0), (0, 127), (127, 0), (127, 127)]:
        assert img[y, x, 3] == 0


def test_top_face_brightest(tmp_path):
    img = one_voxel(tmp_path).astype(int)
    ys, xs = np.nonzero(img[..., 3] == 255)
    bright = img[ys, xs, 0]
    top = bright[ys < 64 - 20].mean()
    low = bright[ys > 64 + 20].mean()
    assert top > low and abs(top - 200) < 6
