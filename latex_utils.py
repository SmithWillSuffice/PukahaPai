#!/usr/bin/env python3
'''
Shared LaTeX formatting helpers for PukahaPai model identifiers and equations.

The TOML model language uses identifiers such as

    lambda_F, alpha_JG, L_JG, f_lambda_F

where underscores are part of the model naming convention.  These helpers
render such names as mathematical subscripts rather than passing raw Python/
TOML identifiers directly to LaTeX.

| Copyright: (c) 2025-2026 Bijou M. Smith
| License: GNU General Public License v3.0 <https://www.gnu.org/licenses/gpl-3.0.html>
'''
import re


# Exact aliases retain the existing notation used by odemodel2tex.py.
# Generic compound identifiers are handled by latex_identifier() below.
SUBS_DICT = {
    'varphi': r'\varphi',
    'varpi': r'\varpi',
    'alpha': r'\alpha',
    'beta': r'\beta',
    'lambda': r'\lambda',
    'theta': r'\theta',
    'pi': r'\pi',
    'Pi': r'\Pi',
    'Phi': r'\Phi',
    'phi': r'\phi',
    'gamma': r'\gamma',
    'Gamma': r'\Gamma',
    'P': r'P',
    'P_init': r'P_0',
    'nu': r'\nu',
    'employment_gap': r'\Delta\lambda',
    '1.0': r'1',
    'productive_Y': r'Y_r',
    'jg_output': r'Y_j',
    'u': r'u',
    'u_init': r'u_0',
    'omega': r'\omega',
    'jg_wage': r'w_j',
    'phi0': r'\phi_0',
}


_IDENTIFIER_RE = re.compile(r'\b[A-Za-z][A-Za-z0-9_]*\b')


def tex_escape(s: str) -> str:
    '''Escape an identifier for use as ordinary LaTeX text.'''
    return s.replace('_', r'\_')


def latex_identifier(name: str) -> str:
    '''Convert one PukahaPai identifier to LaTeX math notation.

    Examples
    --------
    lambda       -> \\lambda
    lambda_F     -> \\lambda_{F}
    alpha_JG     -> \\alpha_{JG}
    L_JG         -> L_{JG}
    F_D          -> F_{D}
    f_lambda_F   -> f_{\\lambda_{F}}

    Exact aliases in SUBS_DICT take precedence.  Otherwise the first
    underscore separates the base symbol from its complete subscript.  This
    is deliberate: model suffixes such as JG and JG0 belong to one subscript.
    '''
    if name in SUBS_DICT:
        return SUBS_DICT[name]

    # A derivative-function name f_x means the named function associated
    # with the complete model variable x.  This is useful where the internal
    # function name itself is displayed rather than converted to dx/dt.
    if name.startswith('f_') and len(name) > 2:
        target = latex_identifier(name[2:])
        return rf'f_{{{target}}}'

    if '_' not in name:
        return name

    base, subscript = name.split('_', 1)
    base_tex = SUBS_DICT.get(base, base)

    # A subscript can itself be a known symbol, although ordinary model
    # suffixes (F, G, JG, init, ...) are intentionally left as written.
    sub_tex = SUBS_DICT.get(subscript, subscript)
    return rf'{base_tex}_{{{sub_tex}}}'


def latex_ode_lhs(name: str, dotted: bool = False) -> str:
    '''Render an ODE key such as f_lambda_F as d(lambda_F)/dt.'''
    if name.startswith('f_'):
        symbol = latex_identifier(name[2:])
        if dotted:
            return rf'\dot{{{symbol}}}'
        return rf'\frac{{d{symbol}}}{{dt}}'

    return latex_identifier(name)


def latex_expression(expr: str, dotted: bool = False, cdots: bool = True) -> str:
    '''Convert identifiers and multiplication operators in a model expression.

    Identifier conversion is token based rather than based on regex word
    boundaries around individual symbol names.  Python treats '_' as a word
    character, so the older approach could not recognise the `lambda` in
    `lambda_F` or the `alpha` in `alpha_JG`.

    References to another ODE RHS, e.g. f_lambda_F, are rendered as the time
    derivative of the complete variable lambda_F.
    '''
    def replace_identifier(match):
        token = match.group(0)
        if token.startswith('f_') and len(token) > 2:
            return latex_ode_lhs(token, dotted=dotted)
        return latex_identifier(token)

    result = _IDENTIFIER_RE.sub(replace_identifier, str(expr))

    if cdots:
        result = re.sub(r'\s*\*\s*', r' \\cdot ', result)
    else:
        result = re.sub(r'\s*\*\s*', ' ', result)

    return result
