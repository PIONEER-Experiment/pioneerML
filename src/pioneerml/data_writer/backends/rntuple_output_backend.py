from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa

from .base_output_backend import OutputBackend
from .factory.registry import REGISTRY as OUTPUT_BACKEND_REGISTRY


_CPP_HELPER_DECLARED = False


def _load_root():
    try:
        import ROOT
    except ImportError as exc:  # pragma: no cover - depends on optional ROOT install
        raise ImportError(
            "The RNTuple output backend requires PyROOT. Install PioneerML with its ROOT support."
        ) from exc

    global _CPP_HELPER_DECLARED
    if not _CPP_HELPER_DECLARED:
        ROOT.gInterpreter.Declare(
            r"""
            #include <ROOT/RNTupleWriter.hxx>
            #include <cstdint>
            #include <memory>
            #include <stdexcept>
            #include <string>
            #include <unordered_map>
            #include <vector>

            namespace PioneerML {
            class ArrowRNTupleSink {
              std::unique_ptr<ROOT::RNTupleWriter> fWriter;
              std::unique_ptr<ROOT::REntry> fEntry;
              std::unordered_map<std::string, std::shared_ptr<bool>> fBool;
              std::unordered_map<std::string, std::shared_ptr<std::int32_t>> fI32;
              std::unordered_map<std::string, std::shared_ptr<std::int64_t>> fI64;
              std::unordered_map<std::string, std::shared_ptr<float>> fF32;
              std::unordered_map<std::string, std::shared_ptr<double>> fF64;
              std::unordered_map<std::string, std::shared_ptr<std::string>> fString;
              std::unordered_map<std::string, std::shared_ptr<std::vector<bool>>> fVBool;
              std::unordered_map<std::string, std::shared_ptr<std::vector<std::int32_t>>> fVI32;
              std::unordered_map<std::string, std::shared_ptr<std::vector<std::int64_t>>> fVI64;
              std::unordered_map<std::string, std::shared_ptr<std::vector<float>>> fVF32;
              std::unordered_map<std::string, std::shared_ptr<std::vector<double>>> fVF64;
              std::unordered_map<std::string, std::shared_ptr<std::vector<std::string>>> fVString;

            public:
              ArrowRNTupleSink(const std::string &path, const std::string &name,
                               const std::vector<std::string> &fieldNames,
                               const std::vector<std::string> &fieldTypes) {
                auto model = ROOT::RNTupleModel::Create();
                for (std::size_t i = 0; i < fieldNames.size(); ++i) {
                  const auto &n = fieldNames[i]; const auto &t = fieldTypes[i];
                  if (t == "bool") model->MakeField<bool>(n);
                  else if (t == "int32") model->MakeField<std::int32_t>(n);
                  else if (t == "int64") model->MakeField<std::int64_t>(n);
                  else if (t == "float") model->MakeField<float>(n);
                  else if (t == "double") model->MakeField<double>(n);
                  else if (t == "string") model->MakeField<std::string>(n);
                  else if (t == "vector<bool>") model->MakeField<std::vector<bool>>(n);
                  else if (t == "vector<int32>") model->MakeField<std::vector<std::int32_t>>(n);
                  else if (t == "vector<int64>") model->MakeField<std::vector<std::int64_t>>(n);
                  else if (t == "vector<float>") model->MakeField<std::vector<float>>(n);
                  else if (t == "vector<double>") model->MakeField<std::vector<double>>(n);
                  else if (t == "vector<string>") model->MakeField<std::vector<std::string>>(n);
                  else throw std::runtime_error("Unsupported RNTuple field type: " + t);
                }
                fWriter = ROOT::RNTupleWriter::Recreate(std::move(model), name, path);
                fEntry = fWriter->CreateEntry();
                for (std::size_t i = 0; i < fieldNames.size(); ++i) {
                  const auto &n = fieldNames[i]; const auto &t = fieldTypes[i];
                  if (t == "bool") fBool[n] = fEntry->GetPtr<bool>(n);
                  else if (t == "int32") fI32[n] = fEntry->GetPtr<std::int32_t>(n);
                  else if (t == "int64") fI64[n] = fEntry->GetPtr<std::int64_t>(n);
                  else if (t == "float") fF32[n] = fEntry->GetPtr<float>(n);
                  else if (t == "double") fF64[n] = fEntry->GetPtr<double>(n);
                  else if (t == "string") fString[n] = fEntry->GetPtr<std::string>(n);
                  else if (t == "vector<bool>") fVBool[n] = fEntry->GetPtr<std::vector<bool>>(n);
                  else if (t == "vector<int32>") fVI32[n] = fEntry->GetPtr<std::vector<std::int32_t>>(n);
                  else if (t == "vector<int64>") fVI64[n] = fEntry->GetPtr<std::vector<std::int64_t>>(n);
                  else if (t == "vector<float>") fVF32[n] = fEntry->GetPtr<std::vector<float>>(n);
                  else if (t == "vector<double>") fVF64[n] = fEntry->GetPtr<std::vector<double>>(n);
                  else if (t == "vector<string>") fVString[n] = fEntry->GetPtr<std::vector<std::string>>(n);
                }
              }
              void SetBool(const std::string &n, bool v) { *fBool.at(n) = v; }
              void SetI32(const std::string &n, std::int32_t v) { *fI32.at(n) = v; }
              void SetI64(const std::string &n, std::int64_t v) { *fI64.at(n) = v; }
              void SetF32(const std::string &n, float v) { *fF32.at(n) = v; }
              void SetF64(const std::string &n, double v) { *fF64.at(n) = v; }
              void SetString(const std::string &n, const std::string &v) { *fString.at(n) = v; }
              void SetVBool(const std::string &n, const std::vector<bool> &v) { *fVBool.at(n) = v; }
              void SetVI32(const std::string &n, const std::vector<std::int32_t> &v) { *fVI32.at(n) = v; }
              void SetVI64(const std::string &n, const std::vector<std::int64_t> &v) { *fVI64.at(n) = v; }
              void SetVF32(const std::string &n, const std::vector<float> &v) { *fVF32.at(n) = v; }
              void SetVF64(const std::string &n, const std::vector<double> &v) { *fVF64.at(n) = v; }
              void SetVString(const std::string &n, const std::vector<std::string> &v) { *fVString.at(n) = v; }
              void Fill() { fWriter->Fill(*fEntry); }
              void Close() { if (fWriter) { fWriter->CommitDataset(); fWriter.reset(); } }
            };
            } // namespace PioneerML
            """
        )
        _CPP_HELPER_DECLARED = True
    return ROOT


def _field_type(data_type: pa.DataType) -> str:
    if pa.types.is_boolean(data_type): return "bool"
    if pa.types.is_int8(data_type) or pa.types.is_int16(data_type) or pa.types.is_int32(data_type): return "int32"
    if pa.types.is_uint8(data_type) or pa.types.is_uint16(data_type): return "int32"
    if pa.types.is_int64(data_type) or pa.types.is_uint32(data_type): return "int64"
    if pa.types.is_float16(data_type) or pa.types.is_float32(data_type): return "float"
    if pa.types.is_float64(data_type): return "double"
    if pa.types.is_string(data_type) or pa.types.is_large_string(data_type): return "string"
    if pa.types.is_list(data_type) or pa.types.is_large_list(data_type):
        return f"vector<{_field_type(data_type.value_type)}>"
    raise TypeError(f"Arrow type {data_type} is not supported by the RNTuple output backend.")


@dataclass
class _RNTupleSink:
    dst_path: Path
    part_path: Path
    ntuple_name: str
    writer: Any = None
    schema: pa.Schema | None = None


@OUTPUT_BACKEND_REGISTRY.register("rntuple")
class RNTupleOutputBackend(OutputBackend):
    """Stream Arrow tables to a ROOT RNTuple."""

    def __init__(self, *, ntuple_name: str = "Events") -> None:
        if not str(ntuple_name).strip():
            raise ValueError("ntuple_name must not be empty.")
        self.ntuple_name = str(ntuple_name)

    def default_extension(self) -> str:
        return ".root"

    def open_sink(self, *, dst_path: Path) -> Any:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        part_path = dst_path.with_suffix(dst_path.suffix + ".part")
        for path in (part_path, dst_path):
            if path.exists(): path.unlink()
        return _RNTupleSink(dst_path=dst_path, part_path=part_path, ntuple_name=self.ntuple_name)

    def append_chunk(self, *, sink: Any, table: pa.Table) -> None:
        if not isinstance(sink, _RNTupleSink):
            raise TypeError(f"Expected _RNTupleSink, got {type(sink).__name__}.")
        if table.num_rows <= 0: return
        if sink.writer is None:
            root = _load_root()
            names = list(table.schema.names)
            types = [_field_type(field.type) for field in table.schema]
            sink.writer = root.PioneerML.ArrowRNTupleSink(str(sink.part_path), sink.ntuple_name, names, types)
            sink.schema = table.schema
        elif not table.schema.equals(sink.schema):
            raise ValueError(f"RNTuple chunk schema changed: expected {sink.schema}, got {table.schema}.")

        setters = {"bool": "SetBool", "int32": "SetI32", "int64": "SetI64", "float": "SetF32",
                   "double": "SetF64", "string": "SetString", "vector<bool>": "SetVBool",
                   "vector<int32>": "SetVI32", "vector<int64>": "SetVI64", "vector<float>": "SetVF32",
                   "vector<double>": "SetVF64", "vector<string>": "SetVString"}
        columns = [col.combine_chunks().to_pylist() for col in table.columns]
        typed = [(field.name, _field_type(field.type), values) for field, values in zip(table.schema, columns)]
        for row in range(table.num_rows):
            for name, field_type, values in typed:
                value = values[row]
                if value is None:
                    raise ValueError(f"Null value in RNTuple field {name!r}; nullable fields are not yet supported.")
                getattr(sink.writer, setters[field_type])(name, value)
            sink.writer.Fill()

    def close_sink(self, *, sink: Any) -> None:
        if not isinstance(sink, _RNTupleSink):
            raise TypeError(f"Expected _RNTupleSink, got {type(sink).__name__}.")
        if sink.writer is not None:
            sink.writer.Close()
            sink.writer = None
            os.replace(sink.part_path, sink.dst_path)

    def write_table_atomic(self, *, table: pa.Table, dst_path: Path) -> None:
        sink = self.open_sink(dst_path=dst_path)
        self.append_chunk(sink=sink, table=table)
        self.close_sink(sink=sink)
