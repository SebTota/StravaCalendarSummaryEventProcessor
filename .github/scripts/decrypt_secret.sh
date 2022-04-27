 #!/bin/sh
    
# Decrypt the file
mkdir $GITHUB_WORKSPACE/secrets

gpg --quiet --batch --yes --decrypt --passphrase="$SECRET_PASSPHRASE" \
--output .github/scripts/secrets.sh .github/scripts/secrets.sh.gpg

. ./.github/scripts/secrets.sh
