"""Unit coverage for the pure forward kinematics used by the historical pose slice.

Every expectation here is computed by hand from a synthetic two- or three-link chain, so the test
does not confirm the implementation by re-running it.
"""

from __future__ import annotations

import math

import pytest

from unirobot.history_fk import (FrozenSceneTree, _quat, _vec, axis_angle_quat, distance_m, quat_mul,
                                 quat_rotate, site_world_position, tcp_from_recorded_state)

IDENTITY = (0.0, 0.0, 0.0, 1.0)


def link(name, parent, joint, joint_type, axis, position, **extra):
    body = {"name": name, "parent_name": parent, "joint_name": joint, "joint_type": joint_type,
            "joint_axis": list(axis), "local_transform": {"position_m": list(position),
                                                          "orientation_xyzw": [0.0, 0.0, 0.0, 1.0]}}
    body.update(extra)
    return body


CHAIN = [link("base_link", None, "base_free", "free", [0, 0, 1], [0, 0, 0.0556]),
         link("link1", "base_link", "joint1", "hinge", [0, 0, 1], [0.1, 0, 0])]


def test_hinge_rotation_is_applied_in_the_child_body_frame():
    tree = FrozenSceneTree(CHAIN)
    poses = tree.body_poses("base_link", (0.0, 0.0, 0.0), IDENTITY, {"joint1": math.pi / 2})
    # link1's origin sits 0.1 m along x; the site is 0.05 m along the child frame's y axis, which a
    # +90 degree turn about z carries onto -x.
    site = site_world_position(poses, "link1", (0.0, 0.05, 0.0))
    assert site[0] == pytest.approx(0.05) and site[1] == pytest.approx(0.0) and site[2] == pytest.approx(0.0)


def test_zero_angle_reproduces_the_plain_offset_sum():
    tree = FrozenSceneTree(CHAIN)
    poses = tree.body_poses("base_link", (0.0, 0.0, 0.0), IDENTITY, {})
    site = site_world_position(poses, "link1", (0.0, 0.05, 0.0))
    assert site == pytest.approx((0.1, 0.05, 0.0))
    # The root body's own local offset is deliberately not composed in: the recorded pose already is
    # the body's world pose, which is the hypothesis the cross-check tests against the alternative.
    assert poses["base_link"][0] == (0.0, 0.0, 0.0)


def test_slide_joint_moves_the_child_along_its_axis():
    chain = [link("base_link", None, "base_free", "free", [0, 0, 1], [0, 0, 0]),
             link("jaw", "base_link", "left_jaw_joint", "slide", [0, -1, 0], [0, 0, 0])]
    poses = FrozenSceneTree(chain).body_poses("base_link", (0.0, 0.0, 0.0), IDENTITY, {"left_jaw_joint": 0.02})
    assert poses["jaw"][0] == pytest.approx((0.0, -0.02, 0.0))


def test_quaternion_helpers_stay_normalised_and_composable():
    rotated = quat_rotate(axis_angle_quat((0.0, 0.0, 1.0), math.pi), (1.0, 0.0, 0.0))
    assert rotated == pytest.approx((-1.0, 0.0, 0.0), abs=1e-12)
    doubled = quat_mul(axis_angle_quat((0, 0, 1), math.pi / 2), axis_angle_quat((0, 0, 1), math.pi / 2))
    assert doubled[3] == pytest.approx(0.0, abs=1e-12)
    assert _quat([0.0, 0.0, 0.0, 0.0]) is None          # a zero quaternion cannot orient anything
    assert _vec(["0.1", 0, 0]) is None                   # strings are not recorded numbers
    assert _vec([0.1, 0, 0, 0]) is None                  # wrong arity is not a vector


def test_tcp_reconstruction_refuses_instead_of_guessing():
    links = CHAIN
    common = {"arm_names": ["joint1"], "base_quaternion_xyzw": [0, 0, 0, 1], "base_position": [0, 0, 0],
              "tcp_parent_body": "link1", "tcp_offset": [0, 0, 0]}
    ok = tcp_from_recorded_state(links, common["arm_names"], [0.0], common["base_position"],
                                common["base_quaternion_xyzw"], common["tcp_parent_body"], common["tcp_offset"])
    assert ok["status"] == "computed" and ok["position_m"] == pytest.approx([0.1, 0.0, 0.0])
    short = tcp_from_recorded_state(links, common["arm_names"], [0.0, 0.1], common["base_position"],
                                    common["base_quaternion_xyzw"], common["tcp_parent_body"], common["tcp_offset"])
    assert short["status"] == "not_computable" and "length" in short["reason"]
    missing_body = tcp_from_recorded_state(links, common["arm_names"], [0.0], common["base_position"],
                                           common["base_quaternion_xyzw"], "no_such_body", common["tcp_offset"])
    assert missing_body["status"] == "not_computable"
    no_position = tcp_from_recorded_state(links, common["arm_names"], [0.0], [None, 0, 0],
                                         common["base_quaternion_xyzw"], common["tcp_parent_body"],
                                         common["tcp_offset"])
    assert no_position["status"] == "not_computable" and no_position["inputs"]["base_position_present"] is False


def test_distance_is_euclidean():
    assert distance_m((0.0, 0.0, 0.0), (0.0, 3.0, 4.0)) == pytest.approx(5.0)




