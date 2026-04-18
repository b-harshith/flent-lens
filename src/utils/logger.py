"""
Flent Lens — Terminal UI Engine
Narrative-driven logging with Rich panels, tables, and dashboards.
"""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.theme import Theme
from datetime import datetime
from contextlib import contextmanager
import config

# ═══════════════════════════════════════════════════════════════════
# THEME
# ═══════════════════════════════════════════════════════════════════
theme = Theme({
    "info":      "cyan",
    "warning":   "yellow",
    "error":     "bold red",
    "success":   "bold green",
    "step":      "bold magenta",
    "highlight": "bold blue",
    "narrative": "italic dim",
    "metric":    "bold cyan",
    "dim":       "dim",
})

console = Console(theme=theme)

# ═══════════════════════════════════════════════════════════════════
# TEAM
# ═══════════════════════════════════════════════════════════════════
TEAM = [
    ("Harshith Bejjanki",  "SM24UBBA047"),
    ("Suneeth Boorgula",   "SM24UBBA016"),
    ("Sudhiksha",          "SM24UBBA033"),
    ("Peddi Sudeeksha",    "SM24UBBA027"),
    ("Vedanth Nagaarur",   "SM24UBBA019"),
]

# ═══════════════════════════════════════════════════════════════════
# BANNER
# ═══════════════════════════════════════════════════════════════════
def print_banner():
    art = """
███████╗██╗     ███████╗███╗   ██╗████████╗
██╔════╝██║     ██╔════╝████╗  ██║╚══██╔══╝
█████╗  ██║     █████╗  ██╔██╗ ██║   ██║   
██╔══╝  ██║     ██╔══╝  ██║╚██╗██║   ██║   
██║     ███████╗███████╗██║ ╚████║   ██║   
╚═╝     ╚══════╝╚══════╝╚═╝  ╚═══╝   ╚═╝"""
    banner = Text()
    for line in art.strip().split("\n"):
        banner.append(line + "\n", style="bold cyan")
    banner.append("\n")
    banner.append("             L E N S", style="bold white")
    banner.append("  \n\n", style="dim")
    banner.append(f"  {config.CITY_NAME} Co-Living Opportunity Analysis\n", style="italic cyan")
    banner.append(f"  Navigate {config.CITY_NAME}'s Co-Living Opportunity Market\n\n", style="dim")

    team_names = " · ".join([name for name, _ in TEAM])
    team_ids   = " · ".join([sid for _, sid in TEAM])
    banner.append("  Team  ", style="bold white")
    banner.append(team_names + "\n", style="")
    banner.append("        ", style="")
    banner.append(team_ids, style="dim")

    console.print()
    console.print(Panel(banner, border_style="cyan", padding=(1, 2), expand=False))
    console.print()

# ═══════════════════════════════════════════════════════════════════
# STAGE HEADER
# ═══════════════════════════════════════════════════════════════════
def print_stage(step_idx, total_steps, name, description=None):
    console.print()
    header = Text()
    header.append(f"STAGE {step_idx}/{total_steps}", style="bold magenta")
    header.append("  ▸  ", style="dim")
    header.append(name, style="bold white")
    console.print(Panel(header, border_style="magenta", expand=True, padding=(0, 1)))
    if description:
        print_narrative(description)

def print_step(step_idx, total_steps, name):
    """Legacy-compatible stage header (no description)."""
    print_stage(step_idx, total_steps, name)

# ═══════════════════════════════════════════════════════════════════
# PRINT FUNCTIONS
# ═══════════════════════════════════════════════════════════════════
def print_success(message):
    console.print(f"  [success]✓[/] {message}")

def print_info(message):
    console.print(f"  [info]ℹ[/] {message}")

def print_warning(message):
    console.print(f"  [warning]⚠[/] {message}")

def print_error(message):
    console.print(f"  [error]✗[/] {message}")

def print_narrative(message):
    console.print(f"  [narrative]▸ {message}[/]")

def print_detail(message):
    console.print(f"    [dim]└─ {message}[/]")

def print_metric(label, value, unit=""):
    suffix = f" {unit}" if unit else ""
    console.print(f"  [metric]│[/] {label}: [highlight]{value}[/]{suffix}")

# ═══════════════════════════════════════════════════════════════════
# DATA DISPLAY
# ═══════════════════════════════════════════════════════════════════
def display_data_table(title, headers, rows, max_rows=8):
    table = Table(title=title, show_header=True, header_style="bold magenta",
                  border_style="dim", padding=(0, 1))
    for h in headers:
        table.add_column(h)
    for row in rows[:max_rows]:
        table.add_row(*[str(v) for v in row])
    console.print(table)

def display_dataframe_summary(df, title="Data Summary"):
    table = Table(title=title, show_header=True, header_style="bold magenta")
    for col in df.columns[:8]:
        table.add_column(col)
    for _, row in df.head(5).iterrows():
        table.add_row(*[str(val)[:20] for val in row[:8]])
    console.print(table)
    console.print(f"    [dim]{len(df)} rows × {len(df.columns)} columns[/]")

# ═══════════════════════════════════════════════════════════════════
# FINAL DASHBOARD
# ═══════════════════════════════════════════════════════════════════
def display_final_dashboard(tier_counts, top5, morans_result, ols_r2, export_paths, elapsed):
    console.print()
    console.print(Panel(
        "[bold white]FLENT LENS — ANALYSIS COMPLETE[/]",
        border_style="green", expand=True
    ))

    # ── Tier Distribution ──
    tier_table = Table(title="Ward Distribution", show_header=True,
                       header_style="bold", border_style="green")
    tier_table.add_column("Tier", style="bold")
    tier_table.add_column("Count", justify="right")
    tier_colors = {"Tier 1": "green", "Tier 2": "yellow", "Tier 3": "red", "Excluded": "dim"}
    for tier_name in ["Tier 1", "Tier 2", "Tier 3", "Excluded"]:
        count = tier_counts.get(tier_name, 0)
        color = tier_colors.get(tier_name, "")
        tier_table.add_row(f"[{color}]{tier_name}[/]", str(count))

    # ── Top 5 ──
    top_table = Table(title="Top 5 Investment Wards", show_header=True,
                      header_style="bold", border_style="cyan")
    top_table.add_column("#", justify="right", style="dim")
    top_table.add_column("Ward", style="bold")
    top_table.add_column("Score", justify="right", style="green")
    top_table.add_column("Arb Margin", justify="right", style="cyan")
    for i, (_, row) in enumerate(top5.iterrows(), 1):
        wname = str(row.get('ward_name', row.get('ward_id', '?')))[:25]
        score = f"{row['OPP_SCORE']:.1f}"
        margin = f"₹{row['arb_margin_best']:,.0f}" if 'arb_margin_best' in row and row['arb_margin_best'] > 0 else "—"
        top_table.add_row(str(i), wname, score, margin)

    console.print(Columns([tier_table, top_table], padding=(2, 4)))

    # ── Validation ──
    if morans_result:
        mi = morans_result.get('moran_i', '—')
        pv = morans_result.get('p_value', '—')
        tag = "[green]CLUSTERED ✓[/]" if morans_result.get('clustered') else "[yellow]RANDOM[/]"
        console.print(f"  [dim]Moran's I:[/] {mi} (p={pv}) → {tag}")
    if ols_r2 is not None:
        console.print(f"  [dim]Arbitrage OLS R²:[/] [bold]{ols_r2:.4f}[/]")

    # ── Exports ──
    console.print(f"\n  [dim]Outputs saved to:[/]")
    for p in export_paths:
        console.print(f"    [dim]→[/] {p}")

    console.print(f"\n  [dim]Total pipeline time:[/] [bold]{elapsed:.1f}s[/]")
    console.print()

# ═══════════════════════════════════════════════════════════════════
# CONTEXT MANAGERS
# ═══════════════════════════════════════════════════════════════════
@contextmanager
def log_process(name):
    """Lightweight spinner — shows working status, prints completion time."""
    start = datetime.now()
    with console.status(f"  → {name}...", spinner="dots", spinner_style="cyan"):
        yield
    elapsed = (datetime.now() - start).total_seconds()
    console.print(f"  [green]✓[/] {name} [dim]({elapsed:.1f}s)[/]")

def progress_bar():
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console, transient=True
    )
