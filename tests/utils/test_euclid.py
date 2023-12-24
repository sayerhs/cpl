# -*- coding: utf-8 -*-

"""Unit tests for euclid module"""

import pytest
import numpy as np
from caelus.utils.euclid import TrMat, Vec

def test_trmat_create():
    """Test matrix creation """
    angle = 45.0
    xrot = TrMat.X(angle)
    qxrot = TrMat.Q(Vec.ihat(), angle)
    assert qxrot == xrot

    yrot = TrMat.Y(angle)
    qyrot = TrMat.Q(Vec.jhat(), angle)
    assert qyrot == yrot

    zrot = TrMat.Z(angle)
    qzrot = TrMat.Q(Vec.khat(), angle)
    assert qzrot == zrot

    assert xrot != yrot
    assert yrot != zrot

    xtmp = xrot[1:, 1:]
    assert np.allclose(np.abs(xtmp), np.sin(np.radians(angle)))
    ztmp = zrot[:-1, :-1]
    assert np.allclose(np.abs(ztmp), np.sin(np.radians(angle)))

def test_trmat_axes_create():
    """Axes based transformations"""
    t1 = TrMat.Y(90.0)
    t2 = TrMat.Z(90.0)
    trot = t2 * t1

    trot_axes = TrMat.axes(
        x=[0.0, 1.0, 0.0],
        y=[0.0, 0.0, 1.0],
        z=[1.0, 0.0, 0.0])
    assert trot_axes == trot

    trot_axes = TrMat.axes(
        x=[0.0, 1.0, 0.0],
        y=[0.0, 0.0, 1.0])
    assert trot_axes == trot

    trot_axes = TrMat.axes(
        y=[0.0, 0.0, 1.0],
        z=[1.0, 0.0, 0.0])
    assert trot_axes == trot

    trot_axes = TrMat.axes(
        x=[0.0, 1.0, 0.0],
        z=[1.0, 0.0, 0.0])
    assert trot_axes == trot

    with pytest.raises(ValueError):
        TrMat.axes(x=[0.0, 1.0, 0.0])

    with pytest.raises(AssertionError):
        TrMat.axes(x=[0.0, 1.0, 0.0], y=[0.0, 1.0, 1.0])

    with pytest.raises(AssertionError):
        TrMat.axes(y=[0.0, 1.0, 0.0], z=[0.0, 1.0, 1.0])

    with pytest.raises(AssertionError):
        TrMat.axes(x=[0.0, 1.0, 0.0], z=[0.0, 1.0, 1.0])

def test_trmat_quarternion():
    """Quarternion checks"""
    t1 = TrMat.Y(90.0)
    t2 = TrMat.Z(90.0)
    trot = t2 * t1

    qrot = TrMat.Q(Vec.xyz(1.0, 1.0, 1.0), angle=120.0)
    assert trot == qrot

def test_trmat_rotations():
    """Rotation checks"""
    angle = 45.0
    ang = np.radians(angle)
    cval = np.cos(ang)
    sval = np.sin(ang)
    xrot = TrMat.X(angle)
    yrot = TrMat.Y(angle)
    zrot = TrMat.Z(angle)

    ivec = Vec.ihat()
    jvec = Vec.jhat()
    kvec = Vec.khat()

    vx1 = xrot * ivec
    assert vx1 == ivec
    vx2 = xrot * jvec
    assert vx2 == np.array([0.0, cval, -sval])
    vx3 = xrot * kvec
    assert vx3 == np.array([0.0, sval, cval])

    vx1 = yrot * jvec
    assert vx1 == jvec
    vx2 = yrot * ivec
    assert vx2 == np.array([cval, 0.0, sval])
    vx3 = yrot * kvec
    assert vx3 == np.array([-sval, 0.0, cval])

    vx1 = zrot * kvec
    assert vx1 == kvec
    vx2 = zrot * ivec
    assert vx2 == np.array([cval, -sval, 0.0])
    vx3 = zrot * jvec
    assert vx3 == np.array([sval, cval, 0.0])

def test_vec():
    """Test vector methods"""
    arr = np.vstack((np.eye(3),
                     np.array([1.0, 1.0, 0.0]),
                     np.array([0.0, 1.0, 1.0])))
    vec = Vec(arr)

    mag = np.array([1.0, 1.0, 1.0, np.sqrt(2.0), np.sqrt(2.0)])
    assert np.allclose(mag, vec.mag)
    assert np.allclose(np.square(mag), vec.mag_sqr)

    assert np.allclose(np.square(mag), vec.dot(vec))
    assert np.allclose(vec * vec, vec.dot(vec))
    assert np.allclose(0.0, np.asarray(vec.cross(vec)))
    assert np.allclose(1.0, np.asarray(vec.unit.mag))

    xcomp = np.array([1.0, 0.0, 0.0, 1.0, 0.0])
    ycomp = np.array([0.0, 1.0, 0.0, 1.0, 1.0])
    zcomp = np.array([0.0, 0.0, 1.0, 0.0, 1.0])
    assert np.allclose(xcomp, vec.x)
    assert np.allclose(ycomp, vec.y)
    assert np.allclose(zcomp, vec.z)

    # Modification of the actual vector
    vec.normalize()
    assert np.allclose(1.0, vec.mag)

def test_vec_rotations():
    """Test rotations"""
    arr = np.vstack((np.eye(3),
                     np.array([1.0, 1.0, 0.0]),
                     np.array([0.0, 1.0, 1.0])))
    vec = Vec(arr)

    expected_arr = np.array([
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.0, -1.0, 0.0],
        [1.0, 0.0, 1.0],
        [0.0, -1.0, 1.0]])
    expected = Vec(expected_arr)

    xrot = TrMat.X(90.0)
    rot_vec = vec * xrot
    assert rot_vec == expected
