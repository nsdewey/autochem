"""
  Functions used for handling and comparing multiple geometries
"""

import itertools
import functools
import numpy
from phydat import ptab
import automol.zmat
import automol.convert.geom
from automol import util
from automol.geom import _base as geom_base


# Assessments of two geomeries
def minimum_distance(geo1, geo2):
    """ get the minimum distance between atoms in geo1 and those in geo2

        :param geo1: molecular geometry 1
        :type geo1: automol molecular geometry data structure
        :param geo2: molecular geometry 2
        :type geo2: automol molecular geometry data structure
        :rtype: float
    """

    xyzs1 = geom_base.coordinates(geo1)
    xyzs2 = geom_base.coordinates(geo2)
    return min(util.vec.distance(xyz1, xyz2)
               for xyz1, xyz2 in itertools.product(xyzs1, xyzs2))


# Calculating quantities used for comparisons
def coulomb_spectrum(geo):
    """ Calculate a Coulomb matrix eigenvalue spectrum where
        the eignevalues are sorted in ascending order.

        :param geo: molecular geometry
        :type geo: automol molecular geometry data structure
        :rtype: tuple(float)
    """

    mat = _coulomb_matrix(geo)
    vals = tuple(sorted(numpy.linalg.eigvalsh(mat)))

    return vals


def _coulomb_matrix(geo):
    """ Calculate the Coulomb matrix wich describes the
        electrostatic interactions between nuclei:

        M[i,j] = 0.5Z_i^2.4 (i=j), Z_iZ_j/R_ij (i!=j

        :param geo: molecular geometry
        :type geo: automol molecular geometry data structure
        :rtype: tuple(tuple(float))
    """

    nums = numpy.array(list(map(ptab.to_number, geom_base.symbols(geo))))
    xyzs = numpy.array(geom_base.coordinates(geo))

    _ = numpy.newaxis
    natms = len(nums)
    diag_idxs = numpy.diag_indices(natms)
    tril_idxs = numpy.tril_indices(natms, -1)
    triu_idxs = numpy.triu_indices(natms, 1)

    zxz = numpy.outer(nums, nums)
    rmr = numpy.linalg.norm(xyzs[:, _, :] - xyzs[_, :, :], axis=2)

    mat = numpy.zeros((natms, natms))
    mat[diag_idxs] = nums ** 2.4 / 2.
    mat[tril_idxs] = zxz[tril_idxs] / rmr[tril_idxs]
    mat[triu_idxs] = zxz[triu_idxs] / rmr[triu_idxs]

    return mat


def distance_matrix(geo):
    """ Form a Natom X Natom matrix containing the distance of all the
        atoms in a molecular geometry.

        :param geo: molecular geometry
        :type geo: automol geometry data structure
        :rtype: numpy.ndarray
    """

    mat = numpy.zeros((len(geo), len(geo)))
    for i in range(len(geo)):
        for j in range(len(geo)):
            mat[i][j] = geom_base.distance(geo, i, j)

    return mat


# Comparisons between two geometries
def almost_equal_coulomb_spectrum(geo1, geo2, rtol=1e-2):
    """ Assess if two molecular geometries have similar coulomb spectrums.

        :param geo1: molecular geometry 1
        :type geo1: automol molecular geometry data structure
        :param geo2: molecular geometry 2
        :type geo2: automol molecular geometry data structure
        :param rtol: Relative tolerance for the distances
        :type rtol: float
        :rtype: bool
    """
    return numpy.allclose(
        coulomb_spectrum(geo1), coulomb_spectrum(geo2), rtol=rtol)


def argunique_coulomb_spectrum(geos, seen_geos=(), rtol=1e-2):
    """ Get indices of unique geometries, by coulomb spectrum.

        :param geos: list of molecular geometries
        :type geos: tuple(automol molecular geometry data structure)
        :param seen_geos: geometries that have been assessed
        :type seen_geos: tuple(automol molecular geometry data structure)
        :param rtol: Relative tolerance for the distances
        :type rtol: float
        :rtype: tuple(int)
    """
    comp_ = functools.partial(almost_equal_coulomb_spectrum, rtol=rtol)
    idxs = _argunique(geos, comp_, seen_items=seen_geos)
    return idxs


def _argunique(items, comparison, seen_items=()):
    """ Get the indices of unique items using some comparison function.

        :param items: items to assess for uniqueness
        :type items: tuple(obj)
        :param comparison: function used to compare items
        :type comparison: function object
        :param seen_items: items that have been assessed
        :type seen_items: tuple(obj)
        :rtype: tuple(int)
    """

    idxs = []
    seen_items = list(seen_items)
    for idx, item in enumerate(items):
        if not any(comparison(item, seen_item) for seen_item in seen_items):
            idxs.append(idx)
            seen_items.append(item)
    idxs = tuple(idxs)

    return idxs


def almost_equal(geo1, geo2, rtol=2e-3):
    """ Assess if the coordinates of two molecular geometries
        are numerically equal.

        :param geo1: molecular geometry 1
        :type geo1: automol molecular geometry data structure
        :param geo2: molecular geometry 2
        :type geo2: automol molecular geometry data structure
        :param rtol: Relative tolerance for the distances
        :type rtol: float
        :rtype: tuple(tuple(float))
    """

    ret = False
    if geom_base.symbols(geo1) == geom_base.symbols(geo2):
        ret = numpy.allclose(
            geom_base.coordinates(geo1),
            geom_base.coordinates(geo2),
            rtol=rtol)

    return ret


def almost_equal_dist_matrix(geo1, geo2, thresh=0.1):
    """form distance matrix for a set of xyz coordinates
    """

    for i in range(len(geo1)):
        for j in range(len(geo1)):
            dist_mat1_ij = geom_base.distance(geo1, i, j)
            dist_mat2_ij = geom_base.distance(geo2, i, j)
            if abs(dist_mat1_ij - dist_mat2_ij) > thresh:
                return False

    return True


def are_torsions_same(geo, geoi, ts_bnds=()):
    """ compare all torsional angle values
    """

    dtol = 0.09
    same_dihed = True

    # Build the Z-Matrix torsion names
    zma = automol.geom.zmatrix(geo, ts_bnds=ts_bnds)
    tors_names = automol.geom.zmatrix_torsion_coordinate_names(
        geo, ts_bnds=ts_bnds)
    zmai = automol.geom.zmatrix(geoi)
    tors_namesi = automol.geom.zmatrix_torsion_coordinate_names(
        geoi, ts_bnds=ts_bnds)

    # Compare the torsions
    for idx, tors_name in enumerate(tors_names):
        val = automol.zmat.value_dictionary(zma)[tors_name]
        vali = automol.zmat.value_dictionary(zmai)[tors_namesi[idx]]
        valip = vali+2.*numpy.pi
        valim = vali-2.*numpy.pi
        vchk1 = abs(val - vali)
        vchk2 = abs(val - valip)
        vchk3 = abs(val - valim)
        if vchk1 > dtol and vchk2 > dtol and vchk3 > dtol:
            same_dihed = False

    return same_dihed


# Checks
def is_unique(lst, lsti, check_dct):
    """ Compare one of many structure features of a geometry to that of
        a list of geometries to see if it is unique.
    """

    unique = True
    for pair in lsti:
        for key, val in check_dct:
            if key != 'stereo' or val is not None:
                kwargs = {}
            else:
                kwargs = {'chk_arg': val}
            if not CHECK_DCT[key](lst, pair, **kwargs):
                unique = False

    return unique


def _ene(lst, lsti, chk_arg=2e-5):
    """ Compare the energies of two geometries.
    """
    ene, enei = lst[0], lsti[0]
    return abs(ene-enei) < chk_arg


def _dist(lst, lsti, chk_arg=3e-1):
    """ Compare the distance matrices of two geometries.
    """
    geo, geoi = lst[1], lsti[1]
    return almost_equal_dist_matrix(geo, geoi, thresh=chk_arg)


def _tors(lst, lsti, chk_arg=()):
    """ Compare the torsions of two geometries
    """
    geo, geoi = lst[1], lsti[1]
    return are_torsions_same(geo, geoi, ts_bnds=chk_arg)


def _stereo(lst, lsti):
    """ Compare the stereochemistry of two geometries
    """
    ich = automol.convert.geom.inchi(lst[1])
    ichi = automol.convert.geom.inchi(lsti[1])
    return bool(ich == ichi)


def _coloumb(lst, lsti, check_arg=1e-2):
    """ Compare the Coulomb spectrum of geometries.
    """
    geo, geoi = lst[1], lsti[1]
    return almost_equal_coulomb_spectrum(geo, geoi, rtol=check_arg)


CHECK_DCT = {
    'ene': _ene,
    'dist': _dist,
    'tors': _tors,
    'stereo': _stereo,
    'coloumb': _coloumb
}
