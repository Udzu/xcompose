# xcompose

[![PyPi](https://img.shields.io/pypi/v/xcompose)](https://pypi.python.org/pypi/xcompose)
[![License](https://img.shields.io/pypi/l/xcompose)](LICENSE)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A simple utility to help configure X11 compose key sequences.

> The repo also hosts an extensive [.XCompose file](Compose) with over 10 000 new sequences; [more details here](Compose.md).

## Installation

```bash
$ pip install xcompose
```

## Requirements

Currently assumes that the system compose key configurations are in `/usr/share/X11/locale/`, while the keysym definitions are in `/usr/include/X11/keysymdef.h`.

Only tested on Ubuntu 24, but should work more widely (though still very much beta quality).

## Usage

```
$ xcompose -h
usage: xcompose [-h] [-f FILE | -S] [-i] [-k KEY] [-s SORT] {add,find,get,validate} ...

Xcompose sequence helper utility.

positional arguments:
  {add,find,get,validate}
    add                 print a new compose sequence
    find                find sequences matching given output
    get                 get sequences matching given key inputs
    validate            validate compose config file

options:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  config file to analyze (instead of user config)
  -S, --system          analyze system config (instead of user config)
  -i, --ignore-include  don't follow any include declarations in the config
  -k KEY, --key KEY     modifier key keysym (default is Multi_key; use ANY for all)
  -s SORT, --sort SORT  sort resulting sequences (options: 'keys', 'value')
```

### Examples
```
$ xcompose find é
<Multi_key> <acute> <e>			: "é"	eacute # LATIN SMALL LETTER E WITH ACUTE
<Multi_key> <e> <acute>			: "é"	eacute # LATIN SMALL LETTER E WITH ACUTE
<Multi_key> <apostrophe> <e>		: "é"	eacute # LATIN SMALL LETTER E WITH ACUTE
<Multi_key> <e> <apostrophe>		: "é"	eacute # LATIN SMALL LETTER E WITH ACUTE

$ xcompose find pound
<Multi_key> <L> <minus>			: "£"	sterling # POUND SIGN
<Multi_key> <minus> <L>			: "£"	sterling # POUND SIGN
<Multi_key> <l> <minus>			: "£"	sterling # POUND SIGN
<Multi_key> <minus> <l>			: "£"	sterling # POUND SIGN

$ xcompose find U+00B5
<Multi_key> <m> <u>			: "µ"	mu # MICRO SIGN
<Multi_key> <slash> <u>			: "µ"	mu # MICRO SIGN
<Multi_key> <u> <slash>			: "µ"	mu # MICRO SIGN

$ xcompose get / =
<Multi_key> <slash> <equal>		: "≠"	U2260 # NOT EQUAL TO

$ xcompose --sort keys get /
<Multi_key> <slash> <minus>		: "⌿"	U233f # / - APL FUNCTIONAL SYMBOL SLASH BAR
<Multi_key> <slash> <slash>		: "\\"	backslash # REVERSE SOLIDUS
<Multi_key> <slash> <less>		: "\\"	backslash # REVERSE SOLIDUS
<Multi_key> <slash> <equal>		: "≠"	U2260 # NOT EQUAL TO
<Multi_key> <slash> <B>			: "Ƀ"	U0243 # LATIN CAPITAL LETTER B WITH STROKE
<Multi_key> <slash> <C>			: "₡"	U20a1 # COLON SIGN
<Multi_key> <slash> <D>			: "Đ"	Dstroke # LATIN CAPITAL LETTER D WITH STROKE
⋮
<Multi_key> <slash> <U2194>		: "↮"	U21AE # LEFT RIGHT ARROW WITH STROKE
<Multi_key> <slash> <U2395>		: "⍁"	U2341 # / ⎕ APL FUNCTIONAL SYMBOL QUAD SLASH

$ xcompose add ɕ c @
<Multi_key> <c> <at> : "ɕ"  U0255   # LATIN SMALL LETTER C WITH CURL

$ xcompose add ć c /
<Multi_key> <c> <slash> : "ć"  U0107   # LATIN SMALL LETTER C WITH ACUTE (conflicts with ¢)

$ echo '<Multi_key> <c> <comma> <quote> : "ḉ"' >> ~/.XCompose  # add a line to .XCompose

$ xcompose validate
[/home/Udzu/.XCompose#116] Unrecognised keysym: quote
[/home/Udzu/.XCompose#116] Missing keysym: expected U1E09
[/home/Udzu/.XCompose#116] Missing comment: expected LATIN SMALL LETTER C WITH CEDILLA AND ACUTE
[/home/Udzu/.XCompose#116] Compose sequence Multi_key + c + comma + quote for 'ḉ' conflicts with 
  [/usr/share/X11/locale/en_US.UTF-8/Compose#428] Multi_key + c + comma for 'ç'
    to ignore this, include the string 'conflict' or 'override' in the comment
    
$ xcompose -S validate  # system config isn't validated by default (only parsed for conflicts)
[/usr/share/X11/locale/en_US.UTF-8/Compose#73] Incorrect comment: LESS-THAN, expected LESS-THAN SIGN
[/usr/share/X11/locale/en_US.UTF-8/Compose#74] Incorrect comment: LESS-THAN, expected LESS-THAN SIGN
[/usr/share/X11/locale/en_US.UTF-8/Compose#75] Incorrect comment: GREATER-THAN, expected GREATER-THAN SIGN
[/usr/share/X11/locale/en_US.UTF-8/Compose#76] Incorrect comment: GREATER-THAN, expected GREATER-THAN SIGN
[/usr/share/X11/locale/en_US.UTF-8/Compose#121] Incorrect keysym: guillemotleft, expected guillemetleft (or U00AB)
[/usr/share/X11/locale/en_US.UTF-8/Compose#122] Incorrect keysym: guillemotright, expected guillemetright (or U00BB)
[/usr/share/X11/locale/en_US.UTF-8/Compose#198] Incorrect comment: ROUBLE SIGN, expected RUBLE SIGN
⋮
[/usr/share/X11/locale/en_US.UTF-8/Compose#253] Incorrect keysym: masculine, expected ordmasculine (or U00BA)
[/usr/share/X11/locale/en_US.UTF-8/Compose#4985] Incorrect comment: ○ \ APL FUNCTIONAL SYMBOL CIRCLE SLOPE, expected APL FUNCTIONAL SYMBOL CIRCLE BACKSLASH
[/usr/share/X11/locale/en_US.UTF-8/Compose#4986] Incorrect comment: \ ○ APL FUNCTIONAL SYMBOL CIRCLE SLOPE, expected APL FUNCTIONAL SYMBOL CIRCLE BACKSLASH
```
