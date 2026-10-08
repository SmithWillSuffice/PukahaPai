#!/usr/bin/env python3
'''
Unit test for the LaTeX Processing for Godley Table PDF's


| Copyright © 2026, Bijou M. Smith
| License: GNU General Public License v3.0  <https://www.gnu.org/licenses/gpl-3.0.html>
'''
from latex_utils import (
    latex_expression,
    latex_identifier,
    latex_ode_lhs,
)

from godley_check import latex_symbol_subs
from odemodel2tex import ode_lhs_tex, substitute_symbols


def test_simple_identifiers():
    assert latex_identifier("P") == "P"
    assert latex_identifier("lambda") == r"\lambda"
    assert latex_identifier("alpha") == r"\alpha"


def test_compound_identifiers():
    assert latex_identifier("lambda_F") == r"\lambda_{F}"
    assert latex_identifier("alpha_JG") == r"\alpha_{JG}"
    assert latex_identifier("L_JG") == r"L_{JG}"
    assert latex_identifier("F_D") == r"F_{D}"


def test_named_ode_function():
    assert latex_identifier("f_lambda_F") == r"f_{\lambda_{F}}"


def test_ode_lhs():
    assert latex_ode_lhs("f_P") == r"\frac{dP}{dt}"
    assert latex_ode_lhs("f_lambda") == r"\frac{d\lambda}{dt}"
    assert latex_ode_lhs("f_lambda_F") == r"\frac{d\lambda_{F}}{dt}"


def test_ode_lhs_dotted():
    assert latex_ode_lhs("f_lambda_F", dotted=True) == r"\dot{\lambda_{F}}"


def test_expression_identifiers():
    expr = "lambda_F * (Gamma - alpha_F)"
    expected = r"\lambda_{F} \cdot (\Gamma - \alpha_{F})"
    assert latex_expression(expr) == expected


def test_expression_derivative_reference():
    expr = "u * (Phi + varpi * f_lambda_F / lambda_F)"
    expected = (
        r"u \cdot (\Phi + \varpi \cdot "
        r"\frac{d\lambda_{F}}{dt} / \lambda_{F})"
    )
    assert latex_expression(expr) == expected


def test_godley_wrapper_without_cdots():
    assert latex_symbol_subs("w_F*L_F") == r"w_{F} L_{F}"
    assert latex_symbol_subs("w_JG*L_JG") == r"w_{JG} L_{JG}"


def test_odemodel_wrappers():
    assert ode_lhs_tex("f_lambda_F") == r"\frac{d\lambda_{F}}{dt}"

    assert (
        substitute_symbols("alpha_F * lambda_F")
        == r"\alpha_{F} \cdot \lambda_{F}"
    )