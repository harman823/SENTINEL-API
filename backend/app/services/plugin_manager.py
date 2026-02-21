"""
Plugin Manager — Hook-based plugin architecture for AutoAPI Intelligence.

Plugins are Python files in `.autoapi/plugins/` directory that register
callbacks for pipeline lifecycle events. This enables custom rules,
custom reporters, and extensions without modifying core code.
"""

from typing import Any, Callable, Dict, List, Optional
from pathlib import Path
import importlib.util
import sys


# ── Hook Types ──
VALID_HOOKS = [
    "before_lint",      # Before linting starts
    "after_lint",       # After lint results are ready
    "before_tests",     # Before test generation
    "after_tests",      # After tests are generated
    "before_security",  # Before security scan
    "after_security",   # After security tests generated
    "before_report",    # Before report generation
    "after_report",     # After report is generated
    "custom_risk_rule", # Add custom risk factors
    "custom_lint_rule", # Add custom lint rules
]


class HookRegistry:
    """Registry for plugin hooks."""

    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {hook: [] for hook in VALID_HOOKS}

    def register(self, hook_name: str, callback: Callable):
        """Register a callback for a specific hook."""
        if hook_name not in self._hooks:
            raise ValueError(f"Unknown hook: {hook_name}. Valid hooks: {VALID_HOOKS}")
        self._hooks[hook_name].append(callback)

    def get_callbacks(self, hook_name: str) -> List[Callable]:
        """Get all callbacks registered for a hook."""
        return self._hooks.get(hook_name, [])


class PluginManager:
    """Discover and load plugins from the plugins directory."""

    DEFAULT_PLUGIN_DIR = ".autoapi/plugins"

    def __init__(self, plugin_dir: Optional[str] = None):
        self.plugin_dir = Path(plugin_dir or self.DEFAULT_PLUGIN_DIR)
        self.registry = HookRegistry()
        self._loaded_plugins: List[str] = []

    def discover_and_load(self) -> List[str]:
        """
        Discover and load all plugins from the plugin directory.

        Each plugin file must have a `register(hooks)` function
        that receives a HookRegistry and registers callbacks.

        Returns:
            List of loaded plugin names
        """
        if not self.plugin_dir.exists():
            return []

        for plugin_file in sorted(self.plugin_dir.glob("*.py")):
            if plugin_file.name.startswith("_"):
                continue
            try:
                self._load_plugin(plugin_file)
                self._loaded_plugins.append(plugin_file.stem)
            except Exception as e:
                print(f"Warning: Failed to load plugin {plugin_file.name}: {e}")

        return self._loaded_plugins

    def _load_plugin(self, plugin_path: Path):
        """Load a single plugin file and call its register function."""
        module_name = f"autoapi_plugin_{plugin_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, plugin_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load spec for {plugin_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Call the register function
        register_fn = getattr(module, "register", None)
        if register_fn is None:
            raise ValueError(f"Plugin {plugin_path.name} has no register(hooks) function")

        register_fn(self.registry)

    def run_hook(self, hook_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute all callbacks for a specific hook.

        Args:
            hook_name: The hook to execute
            context: Pipeline context data passed to callbacks

        Returns:
            Modified context dictionary
        """
        for callback in self.registry.get_callbacks(hook_name):
            try:
                result = callback(context)
                if isinstance(result, dict):
                    context.update(result)
            except Exception as e:
                context.setdefault("plugin_errors", []).append(
                    f"Plugin error in {hook_name}: {e}"
                )

        return context

    @property
    def loaded_plugins(self) -> List[str]:
        """List of successfully loaded plugin names."""
        return self._loaded_plugins
