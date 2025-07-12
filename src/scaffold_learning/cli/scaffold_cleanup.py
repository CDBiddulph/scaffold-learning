#!/usr/bin/env python3
"""Clean up orphaned scaffold-runner Docker containers."""

import subprocess
import sys
import argparse


def get_scaffold_containers():
    """Get list of running scaffold-runner containers."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-q", "--filter", "ancestor=scaffold-runner"],
            capture_output=True,
            text=True,
            check=True,
        )
        container_ids = result.stdout.strip().split('\n')
        return [cid for cid in container_ids if cid]  # Filter out empty strings
    except subprocess.CalledProcessError as e:
        print(f"Error getting container list: {e}", file=sys.stderr)
        return []


def get_container_info(container_ids):
    """Get detailed info about containers."""
    if not container_ids:
        return []
    
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "ancestor=scaffold-runner", 
             "--format", "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.CreatedAt}}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error getting container info: {e}", file=sys.stderr)
        return ""


def kill_containers(container_ids):
    """Kill the specified containers."""
    if not container_ids:
        return True
    
    try:
        subprocess.run(
            ["docker", "kill"] + container_ids,
            check=True,
        )
        print(f"Successfully killed {len(container_ids)} containers")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error killing containers: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Clean up orphaned scaffold-runner containers")
    parser.add_argument(
        "--list-only", 
        action="store_true", 
        help="List containers without killing them"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Kill containers without confirmation"
    )
    
    args = parser.parse_args()
    
    # Get list of scaffold containers
    container_ids = get_scaffold_containers()
    
    if not container_ids:
        print("No scaffold-runner containers found.")
        return 0
    
    # Show container info
    print("Found scaffold-runner containers:")
    info = get_container_info(container_ids)
    print(info)
    
    if args.list_only:
        return 0
    
    # Confirm before killing (unless --force)
    if not args.force:
        response = input(f"Kill {len(container_ids)} containers? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Cancelled.")
            return 0
    
    # Kill containers
    success = kill_containers(container_ids)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())