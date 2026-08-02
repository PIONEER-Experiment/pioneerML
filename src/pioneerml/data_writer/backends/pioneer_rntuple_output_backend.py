from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pyarrow as pa

from .factory.registry import REGISTRY as OUTPUT_BACKEND_REGISTRY
from .rntuple_output_backend import (
    RNTupleOutputBackend,
    _RNTupleSink,
    _field_type,
    _load_root,
)


_ROOT_TYPE_NAMES = {
    "bool": "bool",
    "int32": "std::int32_t",
    "int64": "std::int64_t",
    "float": "float",
    "double": "double",
    "string": "std::string",
    "vector<bool>": "std::vector<bool>",
    "vector<int32>": "std::vector<std::int32_t>",
    "vector<int64>": "std::vector<std::int64_t>",
    "vector<float>": "std::vector<float>",
    "vector<double>": "std::vector<double>",
    "vector<string>": "std::vector<std::string>",
}


@OUTPUT_BACKEND_REGISTRY.register("pioneer_rntuple")
class PioneerRNTupleOutputBackend(RNTupleOutputBackend):
    """Write an RNTuple carrying the canonical PIONEER data-model header.

    This optional backend is the integration boundary between pioneerML and the
    simulation framework.  ROOT and the PIONEER shared libraries are loaded
    only when this backend is selected; the ordinary Parquet and RNTuple
    backends remain independent of the simulation installation.
    """

    def __init__(
        self,
        *,
        ntuple_name: str = "Events",
        tes_namespace: str,
        pioneer_root: str | None = None,
    ) -> None:
        super().__init__(ntuple_name=ntuple_name)
        if not str(tes_namespace).strip():
            raise ValueError("tes_namespace must not be empty.")
        self.tes_namespace = str(tes_namespace)
        configured_root = pioneer_root or os.environ.get("PIONEERSYS")
        if not configured_root:
            raise RuntimeError(
                "The pioneer_rntuple backend requires PIONEERSYS or pioneer_root."
            )
        self.pioneer_root = Path(configured_root).expanduser().resolve()
        self._tes_paths: dict[str, str] | None = None

    def _load_pioneer(self):
        root = _load_root()
        header = (
            self.pioneer_root
            / "shared"
            / "gaudi"
            / "include"
            / "PIEDMDefaultNames.h"
        )
        if not header.is_file():
            raise FileNotFoundError(
                f"Cannot find the PIONEER default-name header at {header}."
            )
        if root.gSystem.Load("libpi_headers.so") < 0:
            raise RuntimeError("Unable to load the PIONEER libpi_headers.so dictionary.")
        if not hasattr(root, "PIDataModelHeader"):
            raise RuntimeError("libpi_headers.so does not expose PIDataModelHeader.")
        declaration = f'#include "{header}"'
        if not root.gInterpreter.Declare(declaration):
            raise RuntimeError(f"Unable to include {header} through ROOT.")
        try:
            namespace = getattr(root.PIEDM, self.tes_namespace)
        except AttributeError as exc:
            raise ValueError(
                f"PIEDMDefaultNames.h has no PIEDM::{self.tes_namespace} namespace."
            ) from exc
        return root, namespace

    def _canonicalize_table(self, table: pa.Table) -> pa.Table:
        _, namespace = self._load_pioneer()
        paths: dict[str, str] = {}
        fields: list[pa.Field] = []
        for field in table.schema:
            try:
                path = str(getattr(namespace, field.name))
            except AttributeError as exc:
                raise ValueError(
                    f"PIEDM::{self.tes_namespace} has no default TES path for "
                    f"output field {field.name!r}."
                ) from exc
            metadata = dict(field.metadata or {})
            metadata[b"pioneer.tes_path"] = path.encode("utf-8")
            fields.append(field.with_metadata(metadata))
            paths[field.name] = path
        self._tes_paths = paths
        schema = pa.schema(fields, metadata=table.schema.metadata)
        return pa.Table.from_arrays(table.columns, schema=schema)

    def append_chunk(self, *, sink: Any, table: pa.Table) -> None:
        canonical = self._canonicalize_table(table)
        super().append_chunk(sink=sink, table=canonical)

    def _finalize_part_file(self, *, sink: _RNTupleSink) -> None:
        if sink.schema is None or self._tes_paths is None:
            return
        root, _ = self._load_pioneer()
        output = root.TFile.Open(str(sink.part_path), "UPDATE")
        if not output or output.IsZombie():
            raise RuntimeError(
                f"Unable to reopen {sink.part_path} to write PIDataModelHeader."
            )
        try:
            header = root.PIDataModelHeader("PIDataModelHeader", "PIDataModelHeader")
            for field in sink.schema:
                storage_type = _ROOT_TYPE_NAMES[_field_type(field.type)]
                header.AddField(field.name, self._tes_paths[field.name], storage_type)
            if header.Write("PIDataModelHeader", root.TObject.kOverwrite) <= 0:
                raise RuntimeError("ROOT failed to write PIDataModelHeader.")
            output.Write()
        finally:
            output.Close()
