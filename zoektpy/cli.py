"""
Command-line interface for the Zoekt client
"""

import json
import sys
from typing import List, Optional

import click
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from rich.panel import Panel

from .client import ZoektClient
from .models import SearchOptions, ListOptions, ListOptionsField
from .utils import evaluate_file_url_template, evaluate_repo_url_template


console = Console()
error_console = Console(stderr=True)  # For stderr

@click.group()
@click.option("--host", default="localhost", help="Zoekt server hostname (Default: localhost)")
@click.option("--port", default=6070, help="Zoekt server port (Default: 6070)")
@click.option("--timeout", default=10.0, help="Request timeout in seconds (Default: 10s)")
@click.option("--debug/--no-debug", default=False, help="Enable debug output (Default: False)")
@click.option("--theme", default="ansi_light", help="Syntax highlighting theme (Pygments styles, e.g., 'monokai', 'vim'; 'ansi_light' by default)")
@click.option('--links/--no-links', default=True, help="Enable or disable clickable links in output (default: True)")
@click.pass_context
def cli(ctx, host, port, timeout, debug, theme, links):
    """ZoektPy - Python client for Zoekt code search"""
    ctx.ensure_object(dict)
    ctx.obj["client"] = ZoektClient(host=host, port=port, timeout=timeout)
    ctx.obj["theme"] = theme
    ctx.obj["links"] = links
    if debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)


@cli.command()
@click.argument("query")
@click.option("--context", "-c", default=3, help="Number of context lines (default: 3)")
@click.option("--max-matches", "-m", default=20, help="Maximum number of matches to display (default: 20)")
@click.option("--json", "output_json", is_flag=True, help="Output raw JSON")
@click.option("--language", "-l", help="Filter by language")
@click.option("--file", "-f", help="Filter by file pattern")
@click.option("--repo", "-r", help="Filter by repository")
@click.option("--case-sensitive", is_flag=True, help="Enable case sensitivity (default: False")
@click.pass_context
def search(ctx, query, context, max_matches, output_json, language, file, repo, case_sensitive):
    """Search code using Zoekt"""
    client = ctx.obj["client"]
    theme = ctx.obj["theme"]
    embed_links = ctx.obj["links"]

    # Build query with filters
    query_parts = [query]
    if language:
        query_parts.append(f"lang:{language}")
    if file:
        query_parts.append(f"file:{file}")
    if repo:
        query_parts.append(f"repo:{repo}")
    if case_sensitive:
        query_parts.append("case:yes")
    
    final_query = " ".join(query_parts)
    
    # Set up search options
    options = SearchOptions(
        NumContextLines=context,
        MaxDocDisplayCount=max_matches,
        ChunkMatches=True,
    )
    
    try:
        result = client.search(final_query, options=options)
        
        # Output as JSON if requested
        if output_json:
            click.echo(result.json(indent=2))
            return
        
        # Rich console output
        console.print(f"[bold green]Found [/bold green][bold yellow]{result.MatchCount}[/bold yellow] "
                      f"[bold green]matches in [/bold green][bold yellow]{result.FileCount}[/bold yellow] "
                      f"[bold green]files[/bold green]")
        console.print()
        
        # Display file matches
        for i, file_match in enumerate(result.Files):
            if i > 0:
                console.print()

            repo = file_match.Repository
            fileurl = evaluate_file_url_template(result.RepoURLs[repo], file_match.Version, file_match.FileName, None, None)
            if file_match.ChunkMatches:
                first_chunk = file_match.ChunkMatches[0]
                fileurl = evaluate_file_url_template(result.RepoURLs[repo], file_match.Version, file_match.FileName,
                    result.LineFragments[repo], first_chunk.BestLineMatch)

            repourl = evaluate_repo_url_template(result.RepoURLs[repo])

            filetext = file_match.FileName
            if fileurl and embed_links:
                filetext = f"[link={fileurl}]{file_match.FileName}[/link]"

            repotext = repo
            if repourl and embed_links:
                repotext = f"[link={repourl}]{repo}[/link]"

            # File header
            console.print(Panel(
                f"[bold blue]{repotext}[/bold blue] [bold cyan]{filetext}[/bold cyan]",
                subtitle=f"Language: {file_match.Language or 'unknown'} | Score: {file_match.Score:.2f}"
            ))
            
            # Display chunk matches
            if file_match.ChunkMatches:
                for chunk in file_match.ChunkMatches:
                    content = chunk.get_decoded_content()
                    syntax = Syntax(content, file_match.Language or "text", line_numbers=True,
                                    start_line=chunk.ContentStart.LineNumber, theme=theme)
                    console.print(syntax)
                    
                    for range_ in chunk.Ranges:
                        line_num = range_.Start.LineNumber
                        console.print(f"[bold green]Match at line {line_num}, "
                                    f"column {range_.Start.Column} to "
                                    f"line {range_.End.LineNumber}, "
                                    f"column {range_.End.Column}[/bold green]")
            
            # Display line matches
            if file_match.LineMatches:
                for line_match in file_match.LineMatches:
                    line_text = line_match.get_decoded_line()
                    context = line_match.get_decoded_context()
                    
                    # Print before context
                    if "before" in context:
                        for before_line in context["before"]:
                            console.print(f"  {before_line}")
                    
                    # Print matched line
                    console.print(f"[bold green]> [/bold green][bold yellow]{line_text}[/bold yellow]")
                    
                    # Print after context
                    if "after" in context:
                        for after_line in context["after"]:
                            console.print(f"  {after_line}")
    
    except Exception as e:
        error_console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("query", default="")
@click.option("--json", "output_json", is_flag=True, help="Output raw JSON")
@click.option("--minimal", is_flag=True, help="Use minimal output format")
@click.pass_context
def list(ctx, query, output_json):
    """List repositories matching a query"""
    client = ctx.obj["client"]
    
    # Set up list options
    field = ListOptionsField.FULL
    options = ListOptions(Field=field)
    
    try:
        result = client.list_repositories(query, options=options)
        
        # Output as JSON if requested
        if output_json:
            click.echo(result.json(indent=2))
            return
        
        # Rich console output
        console.print(f"[bold green]Found [/bold green][bold yellow]{len(result.Repos)}[/bold yellow] "
                      f"[bold green]repositories[/bold green]")
        console.print()
        
        # Create a table
        table = Table(show_header=True, header_style="bold")
        table.add_column("Repository")
        table.add_column("Branches")
        table.add_column("Latest Commit")
        table.add_column("Symbols")
        table.add_column("Files")
        
        # Add rows
        for repo_info in result.Repos:
            repo = repo_info.Repository
            stats = repo_info.Stats
            branches = ", ".join(branch.Name for branch in repo.Branches)
            latest = repo.LatestCommitDate.strftime("%Y-%m-%d") if repo.LatestCommitDate else "-"
            symbols = "Yes" if repo.HasSymbols else "No"
            
            table.add_row(
                repo.Name,
                branches,
                latest,
                symbols,
                str(stats.Documents)
            )
        
        console.print(table)
    
    except Exception as e:
        error_console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


def main():
    """Entry point for the CLI"""
    cli(obj={})


if __name__ == "__main__":
    main()