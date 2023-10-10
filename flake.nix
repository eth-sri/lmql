{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/release-23.05";
    poetry2nix.url = "github:nix-community/poetry2nix";
    poetry2nix.inputs.nixpkgs.follows = "nixpkgs";
    llamaDotCpp.url = "github:ggerganov/llama.cpp";
    flake-utils.url = "github:numtide/flake-utils";
  };
  outputs = { self, nixpkgs, flake-utils, llamaDotCpp, poetry2nix }: let
    llamaDotCppFlake = llamaDotCpp;
    poetry2nixFlake = poetry2nix;
    nonSystemSpecificOutputs = {
      overlays = {
        noSentencePieceCustomMallocOnDarwin = (final: prev: {
          sentencepiece = if prev.stdenv.isDarwin then prev.sentencepiece.override { withGPerfTools = false; } else prev.sentencepiece;
        });
      };
    };
  in nonSystemSpecificOutputs // flake-utils.lib.eachSystem [ "aarch64-darwin" "x86_64-linux" ] (system: let
    version =
      if self.sourceInfo ? "rev"
      then "${self.sourceInfo.lastModifiedDate}-${self.sourceInfo.shortRev}"
      else "dirty";
    pkgs = import nixpkgs {
      inherit system;
      config.allowUnfree = true; # needed for CUDA on Linux
      overlays = [
        nonSystemSpecificOutputs.overlays.noSentencePieceCustomMallocOnDarwin
        poetry2nixFlake.overlay
      ];
    };
    inherit (pkgs) lib;
    llamaDotCppPkg = llamaDotCppFlake.packages.${system}.default;
    mkPoetryEnv = {llamaDotCppPkg ? null, wantHf ? false, wantReplicate ? false}:
      let
        wantLlama = llamaDotCppPkg != null;
      in pkgs.poetry2nix.mkPoetryEnv {
        python = pkgs.python310;
        projectDir = "${self}/scripts/flake.d";
        overrides = import ./scripts/flake.d/overrides.nix {
          inherit (pkgs) poetry2nix;
          inherit llamaDotCppPkg;
        };
        editablePackageSources = {
          lmql = self;
        };
        # huggingface tokenizers used for llama.cpp, replicate
        extras =
          lib.optionals wantLlama [ "llama" ] ++
          lib.optionals (wantHf || wantLlama || wantReplicate) [ "hf" ] ++
          lib.optionals wantReplicate [ "replicate" ];
      };

    poetryEnvBasic = mkPoetryEnv { };
    poetryEnvHf = mkPoetryEnv { wantHf = true; };
    poetryEnvLlamaCpp = mkPoetryEnv { inherit llamaDotCppPkg; };
    poetryEnvReplicate = mkPoetryEnv { wantReplicate = true; };
    poetryEnvAll = mkPoetryEnv { inherit llamaDotCppPkg; wantHf = true; wantReplicate = true; };

    mkLmtpServerApp = {llamaDotCppPkg ? null, ...} @ opts: {
      type = "app";
      program = "${pkgs.writeShellScript "run-lmtp-server" ''
        set -a
        ${if llamaDotCppPkg != null then ''
          PATH=${llamaDotCppPkg}/bin:$PATH
        '' else ""}
        PYTHONPATH=${self}/src
        exec ${mkPoetryEnv opts}/bin/python -m lmql.cli serve-model "$@"
      ''}";
    };
    playgroundStaticContent = pkgs.mkYarnPackage rec {
      pname = "web";
      inherit version;
      src = ./src/lmql/ui/playground;
      yarnLock = "${src}/yarn.lock";
      yarnNix = "${src}/yarn.nix";
      packageJSON = "${src}/package.json";
      dontStrip = true;

      patchPhase  = ''
        find . -type d -name browser-build -exec rm -rf -- {} +
      '';

      DISABLE_ESLINT_PLUGIN = "true";

      buildPhase = ''
        HOME=$(mktemp -d) yarn --offline build
      '';

      distPhase = ''
        shopt -s extglob
        mv "$out"/libexec/web/deps/web/build "$out/content"
        rm -rf -- "$out"/!(content)
      '';
    };
    mkPlaygroundPkg = poetryEnv:
      pkgs.mkYarnPackage rec {
        pname = "lmql-playground-live";
        inherit version;
        src = ./src/lmql/ui/live;
        yarnLock = "${src}/yarn.lock";
        yarnNix = "${src}/yarn.nix";
        packageJSON = "${src}/package.json";
        dontStrip = true;

        buildPhase = ''
          true
        '';

        distPhase = ''
          # We need a Python interpreter with all the dependencies
          mkdir -p -- $out/bin $out/libexec
          ln -s ${poetryEnv}/bin/python "$out/bin/python"
          ln -s ${pkgs.nodejs}/bin/node "$out/bin/node"

          ln -s ${pkgs.writeShellScript "lmql-live-run" ''
            bindir=''${BASH_SOURCE%/*}
            : addr=''${addr:=127.0.0.1} port=''${port:=3000}
            cd "$bindir/../libexec/liveserve/deps/liveserve" || exit
            export PATH=$bindir:$PATH
            export PYTHONPATH=${self}/src:$PYTHONPATH
            export NODE_PATH=$out/libexec/node_modules
            export PORT=$port
            export content_dir=${playgroundStaticContent}/content
            exec "$bindir/node" "live.js"
          ''} "$out/bin/run"
        '';

        meta.mainProgram = "run";
      };  in rec {
    legacyPackages = pkgs;
    apps = rec {
      lmtp-server = lmtp-server-all;
      lmtp-server-basic = mkLmtpServerApp { };
      lmtp-server-hf = mkLmtpServerApp { wantHf = true; };
      lmtp-server-replicate = mkLmtpServerApp { wantReplicate = true; };
      lmtp-server-llamaCpp = mkLmtpServerApp { inherit llamaDotCppPkg; };
      lmtp-server-all = mkLmtpServerApp { inherit llamaDotCppPkg; wantHf = true; wantReplicate = true; };
    };
    packages = rec {
      # If someone just says they want to "run LMQL", let's give them the friendly interface.
      default = playground;

      llamaDotCpp = llamaDotCppPkg;

      python-basic = poetryEnvBasic;
      python-hf = poetryEnvHf;
      python-llamaCpp = poetryEnvLlamaCpp;
      python-replicate = poetryEnvReplicate;
      python-all = poetryEnvAll;

      playground = playground-all;
      playground-basic = mkPlaygroundPkg poetryEnvBasic;
      playground-hf = mkPlaygroundPkg poetryEnvHf;
      playground-llamaCpp = mkPlaygroundPkg poetryEnvLlamaCpp;
      playground-replicate = mkPlaygroundPkg poetryEnvReplicate;
      playground-all = mkPlaygroundPkg poetryEnvAll;

      lmql-docs = pkgs.runCommand "lmql-docs" {
        python = pkgs.python310.withPackages (p: [p.myst-parser p.pydata-sphinx-theme p.sphinx-book-theme p.nbsphinx]);
        docSource = ./docs/source;
      } ''
        PATH=${pkgs.pandoc}/bin:$PATH ${poetryEnvBasic}/bin/sphinx-build "$docSource" "$out"
      '';
    };
    devShells = let
      jsDevPackages = [
        pkgs.yarn
        pkgs.yarn2nix
      ];
      pythonDevPackages = [
        pkgs.pandoc # not python-specific, but used in building docs
        pkgs.poetry
        pkgs.poetry2nix.cli
        (pkgs.python310.withPackages (p: [p.poetry-core]))
      ];
      runtimePackages = [
        pkgs.nodejs
      ];
    in let lmqlDevShell = poetryEnv: extraBuildInputs: poetryEnv.env.overrideAttrs (oldAttrs: {
        shellHook = ''
          PS1='[lmql] '"$PS1"
          lmql() { python -m lmql.cli "$@"; }
        '';
        PYTHONPATH = "${builtins.toString ./src}";
        buildInputs = jsDevPackages ++ pythonDevPackages ++ runtimePackages ++ extraBuildInputs;
      });
    in rec {
      default = lmql-all;
      # python interpreter able to import lmql successfully
      lmql-basic = lmqlDevShell poetryEnvBasic [];
      lmql-hf = lmqlDevShell poetryEnvHf [];
      lmql-llamaCpp = lmqlDevShell poetryEnvLlamaCpp [llamaDotCppPkg];
      lmql-replicate = lmqlDevShell poetryEnvReplicate [];
      lmql-all = lmqlDevShell poetryEnvAll [llamaDotCppPkg];
      # tools to run poetry and yarn2nix, and nothing else
      minimal = pkgs.mkShell {
        name = "minimal-dev-shell";
        buildInputs = jsDevPackages ++ pythonDevPackages;
      };
    };
  });
}
