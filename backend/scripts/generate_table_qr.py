"""
Génère l'image QR code à imprimer et coller sur une table.

La table doit déjà exister en base (créée via POST /api/v1/tables) — ce
script ne fait qu'encoder son qr_token dans une image, il ne touche pas
à la DB.

Usage:
    python scripts/generate_table_qr.py \\
        --qr-token <token renvoyé par l'API> \\
        --label "Table 5" \\
        --frontend-url https://menu.monresto.tn
"""
import argparse

import qrcode


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qr-token", required=True, help="qr_token renvoyé par POST /api/v1/tables")
    parser.add_argument("--label", required=True, help="Nom affiché, ex: 'Table 5'")
    parser.add_argument("--frontend-url", default="http://localhost:3000")
    parser.add_argument("--output", default=None, help="Chemin du fichier PNG de sortie")
    args = parser.parse_args()

    url = f"{args.frontend_url.rstrip('/')}/menu/{args.qr_token}"
    image = qrcode.make(url)

    output_path = args.output or f"qr_{args.label.replace(' ', '_').lower()}.png"
    image.save(output_path)

    print(f"QR généré pour '{args.label}'")
    print(f"  Fichier : {output_path}")
    print(f"  URL encodée : {url}")


if __name__ == "__main__":
    main()
