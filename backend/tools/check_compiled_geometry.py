"""Run on the server in native MuJoCo's environment; no physics state."""
import json
import struct
import unittest

import mujoco
import numpy as np

from export_compiled_geometry import compiled_stl


def forbidden(*args, **kwargs):
    raise AssertionError("Physics state/stepping is forbidden in static geometry checks")


mujoco.MjData = forbidden
mujoco.mj_step = forbidden
mujoco.mj_forward = forbidden


class CompiledGeometryCheck(unittest.TestCase):
    def test_nonuniform_scale_offcentre_rotated_geometry(self):
        vertices = np.array([[2., 3., 4.], [5., 3., 4.], [2., 5., 4.], [2., 3., 5.]])
        scale = np.array([.02, .03, .04])
        xml = '''<mujoco><asset><mesh name="offset" scale=".02 .03 .04"
        vertex="2 3 4 5 3 4 2 5 4 2 3 5" face="0 2 1 0 1 3 0 3 2 1 2 3"/></asset>
        <worldbody><body><geom type="mesh" mesh="offset" pos=".1 -.2 .3"
        quat="0.7071067811865476 0 0 0.7071067811865476"/></body></worldbody></mujoco>'''
        model = mujoco.MjModel.from_xml_string(xml)
        body = compiled_stl(model, 0)
        count, = struct.unpack_from('<I', body, 80)
        facets = np.frombuffer(body, dtype=np.dtype([('normal', '<f4', (3,)), ('vertices', '<f4', (3, 3)), ('attribute', '<u2')]), offset=84, count=count)
        rotation = np.zeros(9); mujoco.mju_quat2Mat(rotation, model.geom_quat[0]); rotation = rotation.reshape(3, 3)
        actual = facets['vertices'].reshape(-1, 3) @ rotation.T + model.geom_pos[0]
        authored_rotation = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
        expected = (vertices * scale) @ authored_rotation.T + [.1, -.2, .3]
        distances = np.linalg.norm(actual[:, None, :] - expected[None, :, :], axis=2)
        error = float(distances.min(axis=1).max())
        self.assertLess(error, 1e-7)
        self.assertLess(float(distances.min(axis=0).max()), 1e-7)
        old_wrong = (vertices * scale) @ rotation.T + model.geom_pos[0]
        old_error = float(np.linalg.norm(old_wrong[:, None, :] - expected[None, :, :], axis=2).min(axis=1).max())
        self.assertGreater(old_error, .01)
        print(json.dumps({'fixture': 'nonuniform_scale_offcentre_rotated_tetrahedron', 'max_body_frame_error_m': error, 'old_raw_stl_compiled_pose_error_m': old_error, 'triangles': count, 'physics_state_calls': 0}))


if __name__ == '__main__':
    unittest.main()
