"""Reconstruction explicite de l'index documentaire."""

from __future__ import annotations

import argparse

from customer_support.rag.pipeline import IndexManuels


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Réindexe les manuels fictifs PX-200.")
    parser.parse_args(argv)
    index = IndexManuels()
    nombre = index.reconstruire()
    print(f"Manuels indexés : {nombre} fragments.")


if __name__ == "__main__":
    main()
