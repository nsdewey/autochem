""" functions for working with rotational bonds and groups

BEFORE ADDING ANYTHING, SEE IMPORT HIERARCHY IN __init__.py!!!!
"""

import itertools
from automol.graph.base._kekule import linear_segments_atom_keys
from automol.graph.base._kekule import kekules_bond_orders_collated
from automol.graph.base._core import atom_keys
from automol.graph.base._core import bond_keys
from automol.graph.base._core import atom_symbols
from automol.graph.base._core import atom_implicit_hydrogens
from automol.graph.base._core import explicit
from automol.graph.base._core import implicit
from automol.graph.base._core import without_dummy_atoms
from automol.graph.base._core import atoms_neighbor_atom_keys
from automol.graph.base._core import atom_neighbor_atom_key
from automol.graph.base._algo import branch_atom_keys
from automol.graph.base._algo import rings_bond_keys


def rotational_bond_keys(
        gra, lin_keys=None, with_h_rotors=True, with_chx_rotors=True):
    """ get all rotational bonds for a graph

    :param gra: the graph
    :param lin_keys: keys to linear atoms in the graph
    """
    gra = explicit(gra)
    sym_dct = atom_symbols(gra)
    ngb_keys_dct = atoms_neighbor_atom_keys(gra)
    bnd_ord_dct = kekules_bond_orders_collated(gra)
    rng_bnd_keys = list(itertools.chain(*rings_bond_keys(gra)))

    def _is_rotational_bond(bnd_key):
        ngb_keys_lst = [ngb_keys_dct[k] - bnd_key for k in bnd_key]

        is_single = max(bnd_ord_dct[bnd_key]) <= 1
        has_neighbors = all(ngb_keys_lst)
        not_in_ring = bnd_key not in rng_bnd_keys

        is_h_rotor = any(set(map(sym_dct.__getitem__, ks)) == {'H'}
                         for ks in ngb_keys_lst)
        is_chx_rotor = is_h_rotor and any(
            sym_dct[k] == 'C' for k in bnd_key)

        return is_single and has_neighbors and not_in_ring and (
            not is_h_rotor or with_h_rotors) and (
            not is_chx_rotor or with_chx_rotors)

    rot_bnd_keys = frozenset(filter(_is_rotational_bond, bond_keys(gra)))
    lin_keys_lst = linear_segments_atom_keys(gra, lin_keys=lin_keys)
    dum_keys = tuple(atom_keys(gra, symb='X'))
    for keys in lin_keys_lst:
        bnd_keys = sorted((k for k in rot_bnd_keys if k & set(keys)),
                          key=sorted)

        # Check whether there are neighboring atoms on either side of the
        # linear segment
        excl_keys = set(keys) | set(dum_keys)

        end_key1 = atom_neighbor_atom_key(
            gra, keys[0], excl_atm_keys=excl_keys)

        excl_keys |= {end_key1}

        end_key2 = atom_neighbor_atom_key(
            gra, keys[-1], excl_atm_keys=excl_keys)

        if end_key1 is None or end_key2 is None:
            has_neighbors = False
        else:
            end_keys = {end_key1, end_key2}
            ngb_keys_lst = [ngb_keys_dct[k] - excl_keys for k in end_keys]
            has_neighbors = all(ngb_keys_lst)

        if not has_neighbors:
            rot_bnd_keys -= set(bnd_keys)
        else:
            rot_bnd_keys -= set(bnd_keys[:-1])

    return rot_bnd_keys


def rotational_groups(gra, key1, key2, dummy=False):
    """ get the rotational groups for a given rotational axis

    :param gra: the graph
    :param key1: the first atom key
    :param key2: the second atom key
    """

    if not dummy:
        gra = without_dummy_atoms(gra)

    grp1 = branch_atom_keys(gra, key2, key1) - {key1}
    grp2 = branch_atom_keys(gra, key1, key2) - {key2}
    grp1 = tuple(sorted(grp1))
    grp2 = tuple(sorted(grp2))
    return grp1, grp2


def rotational_symmetry_number(gra, key1, key2, lin_keys=None):
    """ get the rotational symmetry number along a given rotational axis

    :param gra: the graph
    :param key1: the first atom key
    :param key2: the second atom key
    """
    ngb_keys_dct = atoms_neighbor_atom_keys(without_dummy_atoms(gra))
    imp_hyd_dct = atom_implicit_hydrogens(implicit(gra))

    axis_keys = {key1, key2}
    # If the keys are part of a linear chain, use the ends of that for the
    # symmetry number calculation
    lin_keys_lst = linear_segments_atom_keys(gra, lin_keys=lin_keys)
    for keys in lin_keys_lst:
        if key1 in keys or key2 in keys:
            if len(keys) == 1:
                key1, key2 = sorted(ngb_keys_dct[keys[0]])
            else:
                key1, = ngb_keys_dct[keys[0]] - {keys[1]}
                key2, = ngb_keys_dct[keys[-1]] - {keys[-2]}
                axis_keys |= set(keys)
                break

    sym_num = 1
    for key in (key1, key2):
        if key in imp_hyd_dct:
            ngb_keys = ngb_keys_dct[key] - axis_keys
            if len(ngb_keys) == imp_hyd_dct[key] == 3:
                sym_num = 3
                break
    return sym_num
