#!/bin/bash

MOUNT_POINT="/mnt/datasets"
REMOTE_SERVER="54.208.161.156:/mnt/datasets"

# Create the mount point directory if it doesn't exist
mkdir -p "$MOUNT_POINT"

# Check if the mount point is already mounted
if mountpoint -q "$MOUNT_POINT"; then
    # If already mounted, unmount it first
    echo "Unmounting $MOUNT_POINT..."
    sudo umount "$MOUNT_POINT"
fi

# Mount the remote NFS volume
echo "Mounting $REMOTE_SERVER to $MOUNT_POINT..."
sudo mount -t nfs "$REMOTE_SERVER" "$MOUNT_POINT"

# Verify the mount operation
if mountpoint -q "$MOUNT_POINT"; then
    echo "Successfully mounted $REMOTE_SERVER to $MOUNT_POINT."
else
    echo "Failed to mount $REMOTE_SERVER to $MOUNT_POINT."
    exit 1
fi
