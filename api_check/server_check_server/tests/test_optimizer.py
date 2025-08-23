# Tests for optimizer module
# Framework: pytest
import pytest

# Attempt typical import locations; adjust as needed if repo structure differs
try:
    from api_check.server_check_server import optimizer as optimizer
except Exception:
    try:
        # Fallback: local optimizer.py in same package
        import optimizer  # type: ignore
    except Exception as e:
        optimizer = None
        _import_error = e


@pytest.mark.skipif('optimizer' not in globals() or optimizer is None, reason="optimizer module not importable")
class TestOptimizerPublicAPI:
    def test_module_exports_are_present(self):
        # Validate that key public callables exist; skip gracefully if absent
        expected_symbols = [
            "optimize",
            "Optimizer",
            "DEFAULT_CONFIG",
        ]
        missing = [name for name in expected_symbols if not hasattr(optimizer, name)]
        # If some symbols are truly not part of API, the assertion message guides maintainers
        assert not missing, f"Missing public symbols: {missing}"

    def test_default_config_is_immutable_like(self):
        if not hasattr(optimizer, "DEFAULT_CONFIG"):
            pytest.skip("DEFAULT_CONFIG not exposed")
        cfg = optimizer.DEFAULT_CONFIG
        # Should be a mapping-like
        assert hasattr(cfg, "get")
        # Attempt to mutate and ensure either error or no in-place mutation
        original = dict(cfg) if hasattr(cfg, "items") else dict(cfg.__dict__)
        # Try common mutation paths
        with pytest.raises(TypeError):
            cfg["threshold"] = 0.5  # expect to raise if MappingProxyType or custom frozen
        assert dict(cfg) == original, "DEFAULT_CONFIG should not be mutated in-place"

    @pytest.mark.parametrize(
        "data,expected",
        [
            ([], []),
            ([1], [1]),
            ([3, 1, 2], [1, 2, 3]),  # assuming optimize sorts for a baseline behavior
        ],
    )
    def test_optimize_happy_paths(self, data, expected):
        if not hasattr(optimizer, "optimize"):
            pytest.skip("optimize() not exposed")
        result = optimizer.optimize(data)
        assert isinstance(result, list)
        assert result == expected

    @pytest.mark.parametrize("bad_input", [None, 42, "string", 3.14, {"a": 1}])
    def test_optimize_rejects_invalid_inputs(self, bad_input):
        if not hasattr(optimizer, "optimize"):
            pytest.skip("optimize() not exposed")
        with pytest.raises((TypeError, ValueError)):
            optimizer.optimize(bad_input)  # type: ignore[arg-type]

    def test_optimizer_class_basic_flow(self):
        if not hasattr(optimizer, "Optimizer"):
            pytest.skip("Optimizer class not exposed")
        opt = optimizer.Optimizer()
        # Check common methods exist
        for name in ("fit", "transform", "fit_transform"):
            assert hasattr(opt, name), f"Optimizer missing method {name}"
        # Idempotent no-op behaviors on edge cases
        out = opt.fit_transform([])
        assert out == []
        # If transform alone should be callable after fit on simple data
        opt.fit([3, 2, 1])
        assert opt.transform([3, 2, 1]) == [1, 2, 3]

    def test_optimizer_state_is_isolated_between_instances(self):
        if not hasattr(optimizer, "Optimizer"):
            pytest.skip("Optimizer class not exposed")
        a = optimizer.Optimizer()
        b = optimizer.Optimizer()
        a.fit([1, 1, 1])
        b.fit([3, 2, 1])
        assert a.transform([2, 3, 1]) == [1, 2, 3]
        assert b.transform([2, 3, 1]) == [1, 2, 3]

    def test_handles_duplicate_and_negative_values(self):
        if not hasattr(optimizer, "optimize"):
            pytest.skip("optimize() not exposed")
        data = [0, -1, -1, 2, 2, -3]
        result = optimizer.optimize(data)
        assert result == sorted(data)

    def test_large_input_performance_guardrail(self):
        if not hasattr(optimizer, "optimize"):
            pytest.skip("optimize() not exposed")
        data = list(range(5000, -1, -1))
        result = optimizer.optimize(data)
        # Quick validation; not a benchmark, but ensures it completes and is correct
        assert result[0] == 0 and result[-1] == 5000
        assert result == sorted(data)

    def test_stability_property_if_expected(self):
        # If the optimizer claims stable ordering for equal keys, verify that
        if not hasattr(optimizer, "optimize"):
            pytest.skip("optimize() not exposed")
        class Item:
            def __init__(self, key, tag): self.key, self.tag = key, tag
            def __repr__(self): return f"Item({self.key},{self.tag})"
        data = [Item(1, "a"), Item(1, "b"), Item(1, "c")]
        try:
            out = optimizer.optimize(data, key=lambda x: x.key)  # type: ignore[attr-defined]
        except TypeError:
            pytest.skip("optimize() does not support key parameter")
        assert [x.tag for x in out] == ["a", "b", "c"], "optimize should be stable for equal keys"

    def test_invalid_key_callable(self):
        if not hasattr(optimizer, "optimize"):
            pytest.skip("optimize() not exposed")
        with pytest.raises((TypeError, ValueError)):
            optimizer.optimize([1, 2, 3], key="not-a-func")  # type: ignore[arg-type]

    def test_custom_compare_or_reverse_flag(self):
        if not hasattr(optimizer, "optimize"):
            pytest.skip("optimize() not exposed")
        # reverse behavior if supported
        try:
            out = optimizer.optimize([1, 2, 3], reverse=True)  # type: ignore[attr-defined]
            assert out == [3, 2, 1]
        except TypeError:
            pytest.skip("optimize() does not support reverse flag")