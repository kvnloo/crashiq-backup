"""Test harness only: run the server with the reader_only NE pack treated as active, for the end-to-end check."""
import dataclasses
import runpy

from crashiq import packs

packs.PACKS["NE"] = dataclasses.replace(packs.PACKS["NE"], status="active")
runpy.run_module("crashiq.server", run_name="__main__")
