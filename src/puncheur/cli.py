"""Puncheur CLI — the command-line interface.

Built with Typer for clean, type-hinted commands. All commands support
--json for machine-readable output and --output for HTML report generation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from puncheur import __version__

app = typer.Typer(
    name="puncheur",
    help="Your Ride. Your Hills. Your Playbook.",
    no_args_is_help=True,
)
route_app = typer.Typer(help="Manage ride routes and tagged segments.")
profile_app = typer.Typer(help="Manage rider profile.")
kom_app = typer.Typer(help="KOM attempt planning and warm-up protocols.")
app.add_typer(route_app, name="route")
app.add_typer(profile_app, name="profile")
app.add_typer(kom_app, name="kom")

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"Puncheur v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", help="Show version.", callback=version_callback, is_eager=True
    ),
) -> None:
    """Puncheur — Your Ride. Your Hills. Your Playbook."""


# ── Init ──────────────────────────────────────────────────────────────


@app.command()
def init() -> None:
    """Interactive setup: name, FTP, weight, W'."""
    from puncheur.config import coggan_power_zones
    from puncheur.models.rider import Rider

    console.print(Panel("Welcome to Puncheur", style="bold orange1"))
    name = typer.prompt("Your name")
    ftp = typer.prompt("FTP (watts)", type=int, default=200)
    weight = typer.prompt("Weight (kg)", type=float, default=75.0)
    w_prime = typer.prompt("W' (joules)", type=int, default=20000)
    max_hr = typer.prompt("Max heart rate (bpm)", type=int, default=185)

    rider = Rider(
        name=name,
        ftp=ftp,
        weight_kg=weight,
        power_zones=coggan_power_zones(ftp),
        max_heart_rate=max_hr,
        w_prime=w_prime,
    )
    rider.save()
    console.print(f"\n[green]Profile saved.[/green] FTP: {ftp}W | W/kg: {rider.w_per_kg:.1f}")


# ── Profile ───────────────────────────────────────────────────────────


@profile_app.command("update")
def profile_update(
    ftp: Optional[int] = typer.Option(None, help="Update FTP (watts)."),
    weight: Optional[float] = typer.Option(None, "--weight", help="Update weight (kg)."),
    w_prime: Optional[int] = typer.Option(None, "--wprime", help="Update W' (joules)."),
    max_hr: Optional[int] = typer.Option(None, "--max-hr", help="Update max HR (bpm)."),
) -> None:
    """Update rider profile values."""
    from puncheur.config import coggan_power_zones
    from puncheur.models.rider import Rider

    try:
        rider = Rider.load()
    except FileNotFoundError:
        console.print("[red]No profile found.[/red] Run 'puncheur init' first.")
        raise typer.Exit(code=1)

    if ftp is not None:
        rider.ftp = ftp
        rider.power_zones = coggan_power_zones(ftp)
    if weight is not None:
        rider.weight_kg = weight
    if w_prime is not None:
        rider.w_prime = w_prime
    if max_hr is not None:
        rider.max_heart_rate = max_hr

    rider.save()
    console.print(f"[green]Profile updated.[/green] FTP: {rider.ftp}W | W/kg: {rider.w_per_kg:.1f}")


# ── Route ─────────────────────────────────────────────────────────────


@route_app.command("add")
def route_add(
    name: str = typer.Argument(..., help="Route name (e.g., 'tuesday_ride')."),
    gpx_file: Path = typer.Argument(..., help="Path to GPX file.", exists=True),
) -> None:
    """Add a ride route from a GPX file."""
    import shutil

    from puncheur.config import get_routes_dir
    from puncheur.models.ride_profile import RideProfile

    routes_dir = get_routes_dir()
    dest_gpx = routes_dir / gpx_file.name
    shutil.copy2(gpx_file, dest_gpx)

    profile = RideProfile(name=name, gpx_file=str(dest_gpx))
    profile.save()
    console.print(f"[green]Route '{name}' added.[/green] GPX saved to {dest_gpx}")
    console.print("Tag segments with: puncheur route tag " + name)


@route_app.command("list")
def route_list() -> None:
    """List saved ride profiles."""
    from puncheur.config import get_routes_dir, load_json

    routes_dir = get_routes_dir()
    route_files = sorted(routes_dir.glob("*.json"))

    if not route_files:
        console.print("[dim]No routes saved yet.[/dim] Add one with: puncheur route add")
        return

    table = Table(title="Saved Routes")
    table.add_column("Name", style="bold")
    table.add_column("Segments", justify="right")
    table.add_column("GPX File")

    for rf in route_files:
        data = load_json(rf)
        table.add_row(
            data.get("name", rf.stem),
            str(len(data.get("segments", []))),
            data.get("gpx_file", "—"),
        )

    console.print(table)


@route_app.command("tag")
def route_tag(
    name: str = typer.Argument(..., help="Route name to tag segments on."),
) -> None:
    """Interactively tag segments on a route."""
    from puncheur.models.ride_profile import RideProfile
    from puncheur.models.segment import Segment

    try:
        profile = RideProfile.load(name)
    except FileNotFoundError:
        console.print(f"[red]Route '{name}' not found.[/red]")
        raise typer.Exit(code=1)

    console.print(f"Tagging segments on [bold]{profile.name}[/bold]")
    console.print("Enter segment details (empty name to finish):\n")

    while True:
        seg_name = typer.prompt("Segment name (empty to finish)", default="")
        if not seg_name:
            break

        start_lat = typer.prompt("Start latitude", type=float)
        start_lon = typer.prompt("Start longitude", type=float)
        end_lat = typer.prompt("End latitude", type=float)
        end_lon = typer.prompt("End longitude", type=float)
        seg_type = typer.prompt("Type (climb/sprint/flat)", default="climb")
        duration = typer.prompt("Estimated duration (seconds)", type=float, default=60.0)
        gradient = typer.prompt("Average gradient (%)", type=float, default=5.0)
        notes = typer.prompt("Notes", default="")

        segment = Segment(
            name=seg_name,
            start_lat=start_lat,
            start_lon=start_lon,
            end_lat=end_lat,
            end_lon=end_lon,
            segment_type=seg_type,
            estimated_duration_seconds=duration,
            avg_gradient_pct=gradient,
            notes=notes,
        )
        profile.segments.append(segment)
        console.print(f"  [green]+ {seg_name}[/green]")

    profile.save()
    console.print(f"\n[green]{len(profile.segments)} segments saved.[/green]")


# ── Debrief ───────────────────────────────────────────────────────────


@app.command()
def debrief(
    fit_file: Path = typer.Argument(..., help="Path to FIT file.", exists=True),
    route: Optional[str] = typer.Option(None, help="Route name to match segments against."),
    output: Optional[Path] = typer.Option(None, help="Output HTML report file."),
    compare: Optional[str] = typer.Option(None, help="Compare to last N rides (e.g., 'last3')."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Post-ride debrief — analyze a ride against a tagged route."""
    from puncheur.analytics.matchbook import compute_wbal
    from puncheur.analytics.power_curve import power_duration_curve
    from puncheur.models.rider import Rider
    from puncheur.parsers.fit_parser import parse_fit
    from puncheur.reporting.debrief import generate_debrief

    ride = parse_fit(str(fit_file))
    if not ride.has_power:
        console.print(
            "[red]FIT file contains no power data[/red] — are you using a power meter?"
        )
        raise typer.Exit(code=1)

    try:
        rider = Rider.load()
    except FileNotFoundError:
        console.print("[red]No rider profile found.[/red] Run 'puncheur init' first.")
        raise typer.Exit(code=1)

    # Core analytics
    pdc = power_duration_curve(ride)
    np_val = ride.normalized_power()
    tss = ride.tss(rider.ftp)
    wbal = compute_wbal(ride.power_stream, rider.ftp, rider.w_prime)

    # Segment matching
    segment_matches = []
    if route:
        from puncheur.analytics.segment_matcher import match_segments
        from puncheur.models.ride_profile import RideProfile

        profile = RideProfile.load(route)
        segment_matches = match_segments(ride, profile)

    if json_output:
        import json

        result = {
            "ride": ride.name or str(fit_file),
            "duration_seconds": ride.duration_seconds,
            "avg_power": round(ride.avg_power, 1),
            "normalized_power": round(np_val, 1),
            "tss": round(tss, 1),
            "intensity_factor": round(ride.intensity_factor(rider.ftp), 2),
        }
        console.print(json.dumps(result, indent=2))
        return

    if output:
        report = generate_debrief(ride, rider, pdc, wbal, segment_matches)
        output.write_text(report, encoding="utf-8")
        console.print(f"[green]Report saved to {output}[/green]")
    else:
        # Terminal output
        console.print(Panel(f"[bold]Post-Ride Debrief[/bold]: {ride.name or fit_file.name}"))
        table = Table()
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")
        table.add_row("Duration", f"{ride.duration_seconds / 60:.0f} min")
        table.add_row("Avg Power", f"{ride.avg_power:.0f} W")
        table.add_row("Normalized Power", f"{np_val:.0f} W")
        table.add_row("TSS", f"{tss:.0f}")
        table.add_row("Intensity Factor", f"{ride.intensity_factor(rider.ftp):.2f}")
        table.add_row("W'bal (min)", f"{min(wbal):.0f} J")
        console.print(table)

        if segment_matches:
            console.print("\n[bold]Segment Analysis[/bold]")
            seg_table = Table()
            seg_table.add_column("Segment")
            seg_table.add_column("Power", justify="right")
            seg_table.add_column("Duration", justify="right")
            seg_table.add_column("W'bal Entry", justify="right")
            for sm in segment_matches:
                seg_table.add_row(
                    sm.segment.name,
                    f"{sm.avg_power:.0f} W",
                    f"{sm.duration_seconds:.0f}s",
                    f"{sm.wbal_at_entry:.0f} J",
                )
            console.print(seg_table)


# ── Playbook ──────────────────────────────────────────────────────────


@app.command()
def playbook(
    route_name: str = typer.Argument(..., help="Route name to generate playbook for."),
    output: Optional[Path] = typer.Option(None, help="Output HTML report file."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Pre-ride playbook — strategy and pacing targets for a route."""
    from puncheur.models.ride_profile import RideProfile
    from puncheur.models.rider import Rider
    from puncheur.strategy.playbook import generate_playbook

    try:
        rider = Rider.load()
    except FileNotFoundError:
        console.print("[red]No rider profile found.[/red] Run 'puncheur init' first.")
        raise typer.Exit(code=1)

    try:
        profile = RideProfile.load(route_name)
    except FileNotFoundError:
        console.print(f"[red]Route '{route_name}' not found.[/red]")
        raise typer.Exit(code=1)

    playbook_data = generate_playbook(rider, profile)

    if json_output:
        import json

        console.print(json.dumps(playbook_data, indent=2))
        return

    if output:
        from puncheur.reporting.playbook_report import generate_playbook_report

        report = generate_playbook_report(playbook_data, rider, profile)
        output.write_text(report, encoding="utf-8")
        console.print(f"[green]Playbook saved to {output}[/green]")
    else:
        console.print(Panel(f"[bold]Pre-Ride Playbook[/bold]: {profile.name}"))
        console.print(f"FTP: {rider.ftp}W | W': {rider.w_prime}J | W/kg: {rider.w_per_kg:.1f}")
        console.print(f"Match budget: {playbook_data.get('match_budget', 'N/A')}")

        if "segments" in playbook_data:
            table = Table(title="Segment Targets")
            table.add_column("Segment")
            table.add_column("Target Power", justify="right")
            table.add_column("Strategy")
            for seg in playbook_data["segments"]:
                table.add_row(seg["name"], f"{seg['target_power']}W", seg.get("tactic", ""))
            console.print(table)


# ── KOM ───────────────────────────────────────────────────────────────


@kom_app.command("plan")
def kom_plan(
    segment: str = typer.Option(..., "--segment", help="Segment name."),
    duration: int = typer.Option(..., "--duration", help="Target duration in seconds."),
    output: Optional[Path] = typer.Option(None, help="Output HTML report file."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Plan a KOM attempt on a segment."""
    from puncheur.models.rider import Rider
    from puncheur.strategy.kom_planner import plan_kom_attempt

    try:
        rider = Rider.load()
    except FileNotFoundError:
        console.print("[red]No rider profile found.[/red] Run 'puncheur init' first.")
        raise typer.Exit(code=1)

    plan = plan_kom_attempt(rider, segment, duration)

    if json_output:
        import json

        console.print(json.dumps(plan, indent=2))
        return

    if output:
        from puncheur.reporting.kom_report import generate_kom_report

        report = generate_kom_report(plan, rider)
        output.write_text(report, encoding="utf-8")
        console.print(f"[green]KOM plan saved to {output}[/green]")
    else:
        console.print(Panel(f"[bold]KOM Attempt Plan[/bold]: {segment}"))
        console.print(f"Target duration: {duration}s")
        console.print(f"Target power: {plan.get('target_power', 'N/A')}W")
        console.print(f"Pacing: {plan.get('pacing_strategy', 'N/A')}")
        if "wbal_warning" in plan:
            console.print(f"[yellow]Warning:[/yellow] {plan['wbal_warning']}")


@kom_app.command("warmup")
def kom_warmup(
    duration: int = typer.Option(..., "--duration", help="Target effort duration in seconds."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Get a warm-up protocol for a target effort duration."""
    from puncheur.models.rider import Rider
    from puncheur.strategy.warmup import get_warmup_protocol

    try:
        rider = Rider.load()
    except FileNotFoundError:
        console.print("[red]No rider profile found.[/red] Run 'puncheur init' first.")
        raise typer.Exit(code=1)

    protocol = get_warmup_protocol(rider, duration)

    if json_output:
        import json

        console.print(json.dumps(protocol, indent=2))
        return

    console.print(Panel(f"[bold]Warm-Up Protocol[/bold]: {duration}s effort"))
    console.print(f"Total warm-up time: {protocol['total_minutes']} min\n")
    for step in protocol["steps"]:
        zone_color = "green" if "Z1" in step["zone"] or "Z2" in step["zone"] else "yellow"
        if "Z5" in step["zone"] or "Z6" in step["zone"] or "Z7" in step["zone"]:
            zone_color = "red"
        console.print(f"  [{zone_color}]{step['zone']}[/{zone_color}] {step['description']}")


# ── Fitness ───────────────────────────────────────────────────────────


@app.command()
def fitness(
    weeks: int = typer.Option(6, help="Number of weeks to display."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Show current CTL/ATL/TSB fitness overview."""
    from puncheur.analytics.fitness import load_fitness_data
    from puncheur.models.rider import Rider

    try:
        rider = Rider.load()
    except FileNotFoundError:
        console.print("[red]No rider profile found.[/red] Run 'puncheur init' first.")
        raise typer.Exit(code=1)

    fitness_data = load_fitness_data(rider)

    if json_output:
        import json

        console.print(json.dumps(fitness_data, indent=2))
        return

    console.print(Panel("[bold]Fitness Overview[/bold]"))
    console.print(f"  CTL (Fitness):  {fitness_data.get('ctl', 0):.1f}")
    console.print(f"  ATL (Fatigue):  {fitness_data.get('atl', 0):.1f}")
    console.print(f"  TSB (Form):     {fitness_data.get('tsb', 0):.1f}")

    tsb = fitness_data.get("tsb", 0)
    if tsb > 15:
        console.print("\n  [green]You're fresh — time to race or test.[/green]")
    elif tsb > 0:
        console.print("\n  [green]Good form — ready to perform.[/green]")
    elif tsb > -15:
        console.print("\n  [yellow]Slightly fatigued — manageable.[/yellow]")
    else:
        console.print("\n  [red]Deep fatigue — consider recovery.[/red]")


# ── History ───────────────────────────────────────────────────────────


@app.command()
def history(
    route_name: str = typer.Argument(..., help="Route name to show history for."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Show ride history and trends for a route."""
    from puncheur.analytics.trends import load_route_history

    history_data = load_route_history(route_name)

    if not history_data:
        console.print(f"[dim]No ride history for '{route_name}'.[/dim]")
        return

    if json_output:
        import json

        console.print(json.dumps(history_data, indent=2))
        return

    console.print(Panel(f"[bold]Ride History[/bold]: {route_name}"))
    table = Table()
    table.add_column("Date")
    table.add_column("Avg Power", justify="right")
    table.add_column("NP", justify="right")
    table.add_column("TSS", justify="right")

    for entry in history_data:
        table.add_row(
            entry.get("date", "—"),
            f"{entry.get('avg_power', 0):.0f} W",
            f"{entry.get('np', 0):.0f} W",
            f"{entry.get('tss', 0):.0f}",
        )
    console.print(table)
