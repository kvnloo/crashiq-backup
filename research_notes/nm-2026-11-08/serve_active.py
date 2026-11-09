"""Test harness only: run the server with the reader_only NM pack treated as active, for the end-to-end check."""
import dataclasses
import runpy

from crashiq import packs

packs.PACKS["NM"] = dataclasses.replace(packs.PACKS["NM"], status="active")
runpy.run_module("crashiq.server", run_name="__main__")
