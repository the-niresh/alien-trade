"""Branded ASCII art for the onboarding TUI — an alien head (👽) with a rising
candlestick chart on its brain. Rendered on the welcome screen via a Rich Static,
so Rich markup ([green]…[/]) is allowed for color. Lines are kept equal width so
the head stays symmetric when centered."""

ALIEN_ART = r"""[b cyan]        _.-'''''''''''-._
      .'                 '.
     /                     \
    |   [/][b green]▁   ▃   ▅   █  ╱[/][b cyan]    |
    |   [/][b green]█   █   █   █ ╱[/][b cyan]     |   [dim italic]chart on[/]
    |   [/][b green]█   █   █   █╱[/][b cyan]      |   [dim italic]the brain[/]
    |    [/][dim]‾‾‾‾‾‾‾‾‾‾‾‾‾[/][b cyan]      |
    |                     |
    |   ◣███◤   ◥███◢     |
    |    ▜█▛     ▜█▛      |
     \                   /
      \    ▁▁▁▁▁▁▁      /
       '._   ▔▔▔   _.'
          '-._____.-'[/]"""
