#!/bin/bash

# Configuration
PACKAGE_NAME="SmarteliaClient"
VERSION="1.0"
IDENTIFIER="com.smartelia.client"
INSTALL_DIR="/tmp/SmarteliaClient"
SCRIPTS_DIR="scripts"
BUILD_DIR="build"
OUTPUT_DIR="output"

# Création des répertoires
mkdir -p "$INSTALL_DIR/usr/local/bin"
mkdir -p "$INSTALL_DIR/Library/LaunchDaemons"
mkdir -p "$SCRIPTS_DIR"
mkdir -p "$BUILD_DIR"
mkdir -p "$OUTPUT_DIR"

# Copie des fichiers dans le répertoire d'installation
cp host_client.sh "$INSTALL_DIR/usr/local/bin/"
cp com.smartelia.hostclient.plist "$INSTALL_DIR/Library/LaunchDaemons/"

# Création du script de pré-installation
cat > "$SCRIPTS_DIR/preinstall" << 'EOF'
#!/bin/bash

# Arrêter le service s'il est en cours d'exécution
if [ -f "/Library/LaunchDaemons/com.smartelia.hostclient.plist" ]; then
    launchctl unload "/Library/LaunchDaemons/com.smartelia.hostclient.plist" 2>/dev/null
fi

# Supprimer les anciens fichiers de log
rm -f /var/log/host_client.* 2>/dev/null

exit 0
EOF

# Création du script de post-installation
cat > "$SCRIPTS_DIR/postinstall" << 'EOF'
#!/bin/bash

# Créer les fichiers de logs
mkdir -p /var/log
touch /var/log/host_client.log
touch /var/log/host_client.err
touch /var/log/host_client.out
chmod 666 /var/log/host_client.*

# Définir les permissions
chmod +x /usr/local/bin/host_client.sh
chmod 644 /Library/LaunchDaemons/com.smartelia.hostclient.plist

# Charger le service
launchctl load "/Library/LaunchDaemons/com.smartelia.hostclient.plist"

exit 0
EOF

# Rendre les scripts exécutables
chmod +x "$SCRIPTS_DIR/preinstall"
chmod +x "$SCRIPTS_DIR/postinstall"

# Création du fichier de distribution
cat > "$BUILD_DIR/distribution.xml" << EOF
<?xml version="1.0" encoding="utf-8"?>
<installer-script minSpecVersion="1.000000">
    <title>Smartelia Client</title>
    <organization>com.smartelia</organization>
    <domains enable_localSystem="true"/>
    <options customize="never" require-scripts="true" rootVolumeOnly="true"/>
    <volume-check>
        <allowed-os-versions>
            <os-version min="10.13"/>
        </allowed-os-versions>
    </volume-check>
    <installation-check script="pm_install_check();"/>
    <script>
        function pm_install_check() {
            if(!(system.compareVersions(system.version.ProductVersion,'10.13') >= 0)) {
                my.result.title = 'Incompatible OS Version';
                my.result.message = 'This package requires macOS 10.13 or later.';
                my.result.type = 'Fatal';
                return false;
            }
            return true;
        }
    </script>
    <choices-outline>
        <line choice="com.smartelia.client.choice"/>
    </choices-outline>
    <choice id="com.smartelia.client.choice" title="Smartelia Client">
        <pkg-ref id="$IDENTIFIER"/>
    </choice>
    <pkg-ref id="$IDENTIFIER" auth="Root">#SmarteliaClient.pkg</pkg-ref>
</installer-script>
EOF

# Construction du package
echo "Construction du package..."

# Créer le package de base
pkgbuild --root "$INSTALL_DIR" \
         --scripts "$SCRIPTS_DIR" \
         --identifier "$IDENTIFIER" \
         --version "$VERSION" \
         --install-location "/" \
         "$BUILD_DIR/SmarteliaClient.pkg"

# Créer le package final
productbuild --distribution "$BUILD_DIR/distribution.xml" \
            --package-path "$BUILD_DIR" \
            --version "$VERSION" \
            "$OUTPUT_DIR/SmarteliaClient-$VERSION.pkg"

# Nettoyage
echo "Nettoyage..."
rm -rf "$INSTALL_DIR"
rm -rf "$BUILD_DIR"
rm -rf "$SCRIPTS_DIR"

echo "Package créé avec succès : $OUTPUT_DIR/SmarteliaClient-$VERSION.pkg" 