"""Node lookup cache for efficient relationship resolution."""

import logging
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.graph.connection import Neo4jConnection

logger = logging.getLogger(__name__)
console = Console()


class NodeLookupCache:
    """Cache existing nodes from Phases 1-3 for efficient relationship creation."""

    def __init__(self, connection: Neo4jConnection):
        """
        Initialize the node lookup cache.

        Args:
            connection: Neo4j database connection
        """
        self.connection = connection
        # Key lookups for finding nodes by their natural identifiers
        self.labels: Dict[Tuple[str, str], str] = {}  # {(routine_name, label_name): label_id}
        self.labels_by_line: Dict[
            Tuple[str, int], str
        ] = {}  # {(routine_name, line_number): label_id}
        self.routines: Dict[str, str] = {}  # {routine_name: routine_id}
        self.globals: Dict[str, str] = {}  # {global_name: global_id}
        self.files: Dict[
            str, Tuple[str, Optional[str]]
        ] = {}  # {file_number: (file_id, global_root)}
        self.packages: Dict[str, str] = {}  # {package_name: package_id}
        self.packages_by_prefix: Dict[str, str] = {}  # {prefix: package_id}

    def load_from_neo4j(self) -> bool:
        """
        Pre-load all nodes for efficient lookup during relationship creation.

        Returns:
            True if successful, False otherwise
        """
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Loading existing nodes from database...", total=None
                )

                # Load all Label nodes
                self._load_labels()
                progress.update(task, description="[cyan]Loaded Label nodes")

                # Load all Routine nodes
                self._load_routines()
                progress.update(task, description="[cyan]Loaded Routine nodes")

                # Load all File nodes with global roots
                self._load_files()
                progress.update(task, description="[cyan]Loaded File nodes")

                # Load all Package nodes
                self._load_packages()
                progress.update(task, description="[cyan]Loaded Package nodes")

                # Globals will be loaded after creation in Phase 4
                progress.update(task, description="[green]✅ All nodes loaded")

            return True

        except Exception as e:
            logger.error(f"Failed to load nodes from Neo4j: {e}")
            return False

    def _load_labels(self) -> None:
        """Load all Label nodes into cache."""
        query = """
        MATCH (l:Label)
        RETURN l.label_id as id, l.name as name, 
               l.routine_name as routine, l.line_number as line
        """
        try:
            labels = self.connection.execute_query(query)
            if labels:
                for label in labels:
                    if label.get("routine") and label.get("name"):
                        key = (label["routine"], label["name"])
                        self.labels[key] = label["id"]

                    if label.get("routine") and label.get("line"):
                        line_key = (label["routine"], label["line"])
                        self.labels_by_line[line_key] = label["id"]

                logger.info(f"Loaded {len(self.labels)} labels into cache")
        except Exception as e:
            logger.error(f"Failed to load labels: {e}")

    def _load_routines(self) -> None:
        """Load all Routine nodes into cache."""
        query = "MATCH (r:Routine) RETURN r.routine_id as id, r.name as name"
        try:
            routines = self.connection.execute_query(query)
            if routines:
                for routine in routines:
                    if routine.get("name"):
                        self.routines[routine["name"]] = routine["id"]

                logger.info(f"Loaded {len(self.routines)} routines into cache")
        except Exception as e:
            logger.error(f"Failed to load routines: {e}")

    def _load_files(self) -> None:
        """Load all File nodes with global roots into cache."""
        query = """
        MATCH (f:File) 
        RETURN f.file_id as id, f.number as num, f.global_root as root
        """
        try:
            files = self.connection.execute_query(query)
            if files:
                for file in files:
                    if file.get("num"):
                        self.files[file["num"]] = (file["id"], file.get("root"))

                logger.info(f"Loaded {len(self.files)} files into cache")
        except Exception as e:
            logger.error(f"Failed to load files: {e}")

    def _load_packages(self) -> None:
        """Load all Package nodes into cache."""
        query = """
        MATCH (p:Package) 
        RETURN p.package_id as id, p.name as name, p.prefixes as prefixes
        """
        try:
            packages = self.connection.execute_query(query)
            if packages:
                for package in packages:
                    if package.get("name"):
                        self.packages[package["name"]] = package["id"]

                    # Also map prefixes to packages
                    if package.get("prefixes"):
                        for prefix in package["prefixes"]:
                            self.packages_by_prefix[prefix] = package["id"]

                logger.info(f"Loaded {len(self.packages)} packages into cache")
        except Exception as e:
            logger.error(f"Failed to load packages: {e}")

    def load_globals(self) -> None:
        """Load Global nodes after they are created in Phase 4."""
        query = "MATCH (g:Global) RETURN g.global_id as id, g.name as name"
        try:
            globals_result = self.connection.execute_query(query)
            if globals_result:
                for global_node in globals_result:
                    if global_node.get("name"):
                        self.globals[global_node["name"]] = global_node["id"]

                logger.info(f"Loaded {len(self.globals)} globals into cache")
        except Exception as e:
            logger.error(f"Failed to load globals: {e}")

    def resolve_label(self, routine_name: str, label_name: str) -> Optional[str]:
        """
        Resolve a label reference to its node ID.

        Args:
            routine_name: Name of the routine containing the label
            label_name: Name of the label

        Returns:
            Label node ID if found, None otherwise
        """
        return self.labels.get((routine_name, label_name))

    def resolve_label_by_line(self, routine_name: str, line_num: int) -> Optional[str]:
        """
        Resolve a label by its line number in a routine.

        Args:
            routine_name: Name of the routine
            line_num: Line number in the routine

        Returns:
            Label node ID if found, None otherwise
        """
        return self.labels_by_line.get((routine_name, line_num))

    def resolve_routine(self, routine_name: str) -> Optional[str]:
        """
        Resolve a routine name to its node ID.

        Args:
            routine_name: Name of the routine

        Returns:
            Routine node ID if found, None otherwise
        """
        return self.routines.get(routine_name)

    def resolve_global(self, global_name: str) -> Optional[str]:
        """
        Resolve a global name to its node ID.

        Args:
            global_name: Name of the global (without ^)

        Returns:
            Global node ID if found, None otherwise
        """
        return self.globals.get(global_name)

    def resolve_file(self, file_number: str) -> Optional[Tuple[str, Optional[str]]]:
        """
        Resolve a file number to its node ID and global root.

        Args:
            file_number: File number

        Returns:
            Tuple of (file_id, global_root) if found, None otherwise
        """
        return self.files.get(file_number)

    def resolve_package(self, package_name: str) -> Optional[str]:
        """
        Resolve a package name to its node ID.

        Args:
            package_name: Name of the package

        Returns:
            Package node ID if found, None otherwise
        """
        return self.packages.get(package_name)

    def resolve_package_by_prefix(self, prefix: str) -> Optional[str]:
        """
        Resolve a routine prefix to its package node ID.

        Args:
            prefix: Routine prefix (e.g., "DG" for Registration)

        Returns:
            Package node ID if found, None otherwise
        """
        return self.packages_by_prefix.get(prefix)

    def resolve_file_by_global(self, global_name: str) -> Optional[Tuple[str, str]]:
        """
        Find a file that uses this global as its root.

        Args:
            global_name: Name of the global (without ^)

        Returns:
            Tuple of (file_number, file_id) if found, None otherwise
        """
        global_with_caret = f"^{global_name}"
        for file_num, (file_id, global_root) in self.files.items():
            if global_root and global_root.startswith(global_with_caret):
                return (file_num, file_id)
        return None

    def get_all_labels_in_routine(self, routine_name: str) -> List[Tuple[str, str]]:
        """
        Get all labels in a specific routine.

        Args:
            routine_name: Name of the routine

        Returns:
            List of (label_name, label_id) tuples
        """
        result = []
        for (routine, label), label_id in self.labels.items():
            if routine == routine_name:
                result.append((label, label_id))
        return result

    def get_statistics(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with counts of cached entities
        """
        return {
            "labels": len(self.labels),
            "labels_by_line": len(self.labels_by_line),
            "routines": len(self.routines),
            "globals": len(self.globals),
            "files": len(self.files),
            "packages": len(self.packages),
            "packages_by_prefix": len(self.packages_by_prefix),
        }

    def validate_cache(self) -> bool:
        """
        Validate that the cache has been properly loaded.

        Returns:
            True if cache contains expected data, False otherwise
        """
        stats = self.get_statistics()

        if stats["labels"] == 0:
            logger.warning("No labels found in cache")
            return False

        if stats["routines"] == 0:
            logger.warning("No routines found in cache")
            return False

        if stats["files"] == 0:
            logger.warning("No files found in cache")
            return False

        if stats["packages"] == 0:
            logger.warning("No packages found in cache")
            return False

        logger.info(f"Cache validated with {sum(stats.values())} total entries")
        return True
