# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# pylint: disable=invalid-name, no-else-return

"""\
Vectors, transformations and reference frames
-------------------------------------------


"""

import numpy as np

class TrMat(np.ndarray):
    """Transformation and rotation matrices

    Defines a 3x3 matrix datatype that represents a coordinate transformation
    or rotation. The matrix is defined such that ``[A] {u}`` results in the
    transformation of the components of the vector ``{u}`` in the inertial
    frame into components in the local frame of reference, and ``{u}^T [A]``
    results in the transformation of the local components into inertial frame.
    The latter can also be viewed as a rotation of the vector by the desired angle.

    .. code-block:: python

       # Matrix creation options
       m1 = TrMat.I()                              # Identity transformation
       m2 = TrMat.X(angle=30.0)                    # Rotated frame about x-axis
       m3 = TrMat.Y(angle=45.0)                    # Rotated frame about y-axis
       m4 = TrMat.Z(angle=60.0)                    # Rotated frame about z-axis

       m5 = m4 * m3                                # Frame rotations Y->Z (y followed by z)
       m6 = m3 * m4                                # Frame rotations Z->Y

       m7 = TrMat.Q(axis=Vec.ihat(), angle=30.0)   # Quarternion rotation
       m7 == m2                                    # Are transformations equivalent?

       m8 = TrMat.Z(90.0) * TrMat.Y(90.0)          # Y->Z transform
       m9 = TrMat.Q(Vec.xyz(1.0, 1.0, 1.0), 120.0) # Quarternion
       m8 == m9                                    # returns True

       # Vector transformation (``[A] {u}``)
       v1 = m2 * Vec.jhat()
       v2 = m3 * Vec.ihat()

       # Vector rotations (``{u}^T [A]``)
       v3 = vec.jhat() * m2
       v4 = vec.khat() * m3
    """

    _dtype = np.double
    _dim = 3

    def __new__(cls, inp_array):
        obj = np.asarray(inp_array).view(cls)
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        assert self.shape == (self._dim, self._dim), "Cannot coerce object to transformation matrix"

    @classmethod
    def I(cls):
        """Identity transformation matrix"""
        return np.eye(cls._dim).view(cls)

    @classmethod
    def X(cls, angle):
        """Rotation about x-axis

        Args:
            angle (double): Angle of rotation in degrees, anti-clockwise is positive
        """
        ang = np.radians(angle)
        cval = np.cos(ang)
        sval = np.sin(ang)
        mat = np.zeros((cls._dim, cls._dim), dtype=cls._dtype)
        mat[0, 0] = 1.0
        mat[1, 1] = cval
        mat[1, 2] = sval
        mat[2, 1] = -sval
        mat[2, 2] = cval
        return mat.view(cls)

    @classmethod
    def Y(cls, angle):
        """Rotation about y-axis

        Args:
            angle (double): Angle of rotation in degrees, anti-clockwise is positive
        """
        ang = np.radians(angle)
        cval = np.cos(ang)
        sval = np.sin(ang)
        mat = np.zeros((cls._dim, cls._dim), dtype=cls._dtype)
        mat[1, 1] = 1.0
        mat[0, 0] = cval
        mat[0, 2] = -sval
        mat[2, 0] = sval
        mat[2, 2] = cval
        return mat.view(cls)

    @classmethod
    def Z(cls, angle):
        """Rotation about z-axis

        Args:
            angle (double): Angle of rotation in degrees, anti-clockwise is positive
        """
        ang = np.radians(angle)
        cval = np.cos(ang)
        sval = np.sin(ang)
        mat = np.zeros((cls._dim, cls._dim), dtype=cls._dtype)
        mat[2, 2] = 1.0
        mat[0, 0] = cval
        mat[0, 1] = sval
        mat[1, 0] = -sval
        mat[1, 1] = cval
        return mat.view(cls)

    @classmethod
    def Q(cls, axis, angle):
        """A quarternion rotation

        Args:
            axis (Vec): A vector about which rotation is performed
            angle (double): Angle of rotation in degrees
        """
        ax = np.asarray(axis)
        assert ax.shape == (cls._dim,), "Inconsistent shape for axis"
        ang = -1.0 * np.radians(angle)
        cval = np.cos(0.5 * ang)
        sval = np.sin(0.5 * ang)
        mag = np.linalg.norm(ax)
        q0 = cval
        q1 = sval * axis[0] / mag
        q2 = sval * axis[1] / mag
        q3 = sval * axis[2] / mag
        mat = np.empty((cls._dim, cls._dim), dtype=cls._dtype)
        mat[0, 0] = q0 * q0 + q1 * q1 - q2 * q2 - q3 * q3
        mat[0, 1] = 2.0 * (q1 * q2 - q0 * q3)
        mat[0, 2] = 2.0 * (q0 * q2 + q1 * q3)
        mat[1, 0] = 2.0 * (q1 * q2 + q0 * q3)
        mat[1, 1] = q0 * q0 - q1 * q1 + q2 * q2 - q3 * q3
        mat[1, 2] = 2.0 * (q2 * q3 - q0 * q1)
        mat[2, 0] = 2.0 * (q1 * q3 - q0 * q2)
        mat[2, 1] = 2.0 * (q0 * q1 + q2 * q3)
        mat[2, 2] = q0 * q0 - q1 * q1 - q2 * q2 + q3 * q3
        return mat.view(cls)

    @classmethod
    def axes(cls, x=None, y=None, z=None):
        """Create a transformation matrix from given vectors for the reference frame

        One of ``x, y, z`` can be None, and it will be computed as the cross
        product of the other two vectors.

        This method will raise an exception if at least two vectors are not
        provided, and if the vectors provided doesn't form an orthogonal basis.
        """
        num_none = np.sum([1 for v in [x, y, z] if v is None])
        if num_none > 1:
            raise ValueError("Only one of x, y, z, can be None")
        if x is None:
            dotp = np.dot(y, z) / (np.linalg.norm(y) * np.linalg.norm(z))
            assert np.allclose(dotp, 0.0), "y and z are not orthogonal"
            x = np.cross(y, z)
        elif y is None:
            dotp = np.dot(z, x) / (np.linalg.norm(z) * np.linalg.norm(x))
            assert np.allclose(dotp, 0.0), "z and x are not orthogonal"
            y = np.cross(z, x)
        elif z is None:
            dotp = np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y))
            assert np.allclose(dotp, 0.0), "x and y are not orthogonal"
            z = np.cross(x, y)
        else:
            zunit = z / np.linalg.norm(z)
            zcross = np.cross(x, y) / (np.linalg.norm(x) * np.linalg.norm(y))
            assert np.allclose(zcross, zunit), "Vectors are not orthogonal"

        mat = np.vstack((
            np.asarray(x, dtype=cls._dtype),
            np.asarray(y, dtype=cls._dtype),
            np.asarray(z, dtype=cls._dtype)))
        return mat.view(cls)

    @classmethod
    def scale(cls, x=1.0, y=1.0, z=1.0):
        """Scaling transformation"""
        return (np.eye(cls._dim) * np.array([x, y, z])).view(cls)

    @classmethod
    def from_dict(cls, opts):
        """Create a transformation matrix from dictionary

        Valid forms of input for the dictionary:

        .. code-block:: yaml

           # Quarternion representation
           rotation_type: quarternion
           axis: [1.0, 1.0, 1.0]
           angle: 120.0

           # Rotation about X-axis
           rotation_type: rot_x             # rot_x, rot_y, or rot_z
           angle: 90.0

           # Axes specification
           rotation_type: axes
           xdir: [0.0, 1.0, 0.0]
           ydir: [0.0, 0.0, 1.0]
        """
        valid_types = "quaternion rot_x rot_y rot_z axes".split()
        rot_type = opts.get("rotation_type", "quaternion")
        if rot_type not in valid_types:
            raise KeyError("Invalid rotation_type: %s"%rot_type)
        tmat = None
        if rot_type == "quaternion":
            axis = np.asarray(opts["axis"])
            angle = opts["angle"]
            tmat = cls.Q(axis=axis, angle=angle)
        elif rot_type == "rot_x":
            angle = opts["angle"]
            tmat = cls.X(angle=angle)
        elif rot_type == "rot_y":
            angle = opts["angle"]
            tmat = cls.Y(angle=angle)
        elif rot_type == "rot_z":
            angle = opts["angle"]
            tmat = cls.Z(angle=angle)
        else:
            xdir = opts.get("xdir", None)
            ydir = opts.get("ydir", None)
            zdir = opts.get("zdir", None)
            tmat = cls.axes(x=xdir, y=ydir, z=zdir)
        return tmat

    def __getitem__(self, *args, **kwargs):
        return np.asarray(self).__getitem__(*args, **kwargs)

    def __mul__(self, other):
        if isinstance(other, TrMat):
            return np.einsum('ij,jk->ik', self, other).view(self.__class__)
        elif isinstance(other, Vec):
            return np.einsum('ij,...j->...i', self, other).view(other.__class__)
        return super().__mul__(other)

    def __eq__(self, other):
        return (isinstance(other, np.ndarray)
                and self.shape == other.shape
                and np.allclose(np.asarray(self), np.asarray(other)))

    def __ne__(self, other):
        return not self.__eq__(other)

class Vec(np.ndarray):
    """Vector and array of vectors

    This class provides a thin wrapper around ``numpy.ndarray`` for
    manipulating vectors. The vectors can be multi-dimensional arrays with the
    last dimension being equal to 3.

    .. code-block:: python

       # Vector creation
       vx = 10.0 * Vec.ihat()
       vy = 20.0 * Vec.jhat()
       vz = 30.0 * Vec.khat()
       # Create a list of vectors
       arr = np.vstack((np.eye(3),
                        np.array([1.0, 1.0, 0.0]),
                        np.array([0.0, 1.0, 1.0])))
       # Initialize the vector field
       vec = Vec(arr)

       # Properties
       vec.x           # x-component
       vec.mag         # Magnitude
       vec.mag_sqr     # Square of magnitude
       vec.unit        # Unit vectors
       vec.normalize() # In-place modification to unit vectors

       # Dot product
       v1 = vec.dot(vz)
       v2 = vec * vz
       v3 = vec * vec

       # Cross product
       v4 = vec.cross(vec)

       # Transformations and rotations
       rot_mat = TrMat.Q(axis=Vec.ihat(), angle=45.0) # Transformation matrix
       v5 = vec * rot_mat                             # Rotation of the vector
       v6 = rot_mat * vec                             # Transformation to ref.frame
    """
    _vdim = 3

    def __new__(cls, inp_array):
        obj = np.asarray(inp_array).view(cls)
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        assert self.shape[-1] == self._vdim, "Not a valid array for vector"

    def __eq__(self, other):
        return (isinstance(other, np.ndarray)
                and self.shape == other.shape
                and np.allclose(np.asarray(self), np.asarray(other)))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __getitem__(self, *args, **kwargs):
        return np.asarray(self).__getitem__(*args, **kwargs)

    @classmethod
    def zero(cls):
        """A zero vector"""
        return np.zeros((cls._vdim,)).view(cls)

    @classmethod
    def ihat(cls):
        """Unit vector in x-direction"""
        return np.asarray([1.0, 0.0, 0.0]).view(cls)

    @classmethod
    def jhat(cls):
        """Unit vector in y-direction"""
        return np.asarray([0.0, 1.0, 0.0]).view(cls)

    @classmethod
    def khat(cls):
        """Unit vector in z-direction"""
        return np.asarray([0.0, 0.0, 1.0]).view(cls)

    @classmethod
    def xyz(cls, x=0.0, y=0.0, z=0.0):
        """Create a vector from components"""
        return np.array([x, y, z]).view(cls)

    @classmethod
    def cyl(cls, r, phi=0.0, z=0.0):
        """Create a vector from cylindrical coordinates"""
        ang = np.radians(phi)
        return np.asarray([
            r * np.cos(ang),
            r * np.sin(ang),
            z]).view(cls)

    def __mul__(self, other):
        if isinstance(other, TrMat):
            return np.einsum('...j,jk->...k', self, other).view(self.__class__)
        elif isinstance(other, Vec):
            return np.einsum('...i,...i->...', self, other)
        else:
            return super().__mul__(other)

    def dot(self, b, out=None):
        """Dot product of two vectors

        ``v1.dot(v2)`` is equivalent to ``v1 * v2``. However, this method can
        take an additional argument ``out`` to fill that array instead of
        creating a new one.
        """
        if out:
            return np.einsum('...i,...i->...', self, b, out=out)
        return np.einsum('...i,...i->...', self, b)

    def cross(self, other):
        """Cross product"""
        return np.cross(self, other).view(self.__class__)

    @property
    def x(self):
        """Return x component"""
        if self.ndim == 1:
            return self[0]
        else:
            return self[..., 0].view(np.ndarray)

    @property
    def y(self):
        """Return y component"""
        if self.ndim == 1:
            return self[1]
        else:
            return self[..., 1].view(np.ndarray)

    @property
    def z(self):
        """Return y component"""
        if self.ndim == 1:
            return self[2]
        else:
            return self[..., 2].view(np.ndarray)


    @property
    def mag(self):
        """Magnitude of the vector"""
        return np.linalg.norm(self, axis=-1)

    @property
    def mag_sqr(self):
        """Square of the magnitude"""
        return np.sum(np.square(self).view(np.ndarray), axis=1)

    @property
    def unit(self):
        """Unit vectors"""
        return (self / self.mag[..., np.newaxis]).view(self.__class__)

    def normalize(self):
        """Normalize the vectors to unit vectors"""
        self /= self.mag[..., np.newaxis]
        return self
