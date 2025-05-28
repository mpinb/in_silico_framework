from getting_started import generate_param_files_with_valid_references
from mechanisms.l5pt import load_mechanisms, compile_l5pt_mechanisms

if __name__ == "__main__":
    compile_l5pt_mechanisms(force_recompile=False)
    load_mechanisms()
    generate_param_files_with_valid_references()