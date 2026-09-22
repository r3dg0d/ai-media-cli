{
  description = "ai-media-cli — local-first AI media tooling";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python311;
        pythonEnv = python.withPackages (ps: with ps; [
          pip
          rich
          pillow
          pytest
          tomli-w
        ]);
      in {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.ruff
            pkgs.git
            pkgs.chafa
            pkgs.imv
          ];
          shellHook = ''
            export PYTHONPATH="$PWD/src:$PYTHONPATH"
            echo "ai-media-cli nix shell — run: pip install -e '.[dev]' && pytest"
          '';
        };
        packages.default = pkgs.writeShellScriptBin "ai-media-info" ''
          echo "ai-media-cli flake — install via pip from repo root"
        '';
      });
}
