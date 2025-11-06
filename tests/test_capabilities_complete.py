"""Complete coverage tests for BackendCapabilities."""

import pytest
from genro_storage.capabilities import BackendCapabilities


class TestBackendCapabilitiesComplete:
    """Test all methods of BackendCapabilities for complete coverage."""

    def test_equality_same_capabilities(self):
        """Test __eq__ with identical capabilities."""
        caps1 = BackendCapabilities(
            read=True,
            write=True,
            delete=True,
            mkdir=True,
            readonly=False,
            versioning=True,
            version_listing=True,
            version_access=True,
            metadata=True,
            presigned_urls=True,
            public_urls=False,
        )

        caps2 = BackendCapabilities(
            read=True,
            write=True,
            delete=True,
            mkdir=True,
            readonly=False,
            versioning=True,
            version_listing=True,
            version_access=True,
            metadata=True,
            presigned_urls=True,
            public_urls=False,
        )

        assert caps1 == caps2

    def test_equality_different_capabilities(self):
        """Test __eq__ with different capabilities."""
        caps1 = BackendCapabilities(read=True, write=True, delete=True)
        caps2 = BackendCapabilities(read=True, write=False, delete=False)

        assert caps1 != caps2

    def test_equality_with_non_capabilities_object(self):
        """Test __eq__ with non-BackendCapabilities object."""
        caps = BackendCapabilities(read=True, write=True)

        assert caps != "not a capabilities object"
        assert caps != 42
        assert caps != None

    def test_hash_same_for_equal_capabilities(self):
        """Test __hash__ returns same hash for equal capabilities."""
        caps1 = BackendCapabilities(read=True, write=True, delete=True)
        caps2 = BackendCapabilities(read=True, write=True, delete=True)

        assert hash(caps1) == hash(caps2)

    def test_hash_different_for_different_capabilities(self):
        """Test __hash__ returns different hash for different capabilities."""
        caps1 = BackendCapabilities(read=True, write=True, delete=True)
        caps2 = BackendCapabilities(read=True, write=False, delete=False)

        # Different capabilities should (usually) have different hashes
        # Note: hash collisions are possible but extremely rare
        assert hash(caps1) != hash(caps2)

    def test_repr(self):
        """Test __repr__ returns valid representation."""
        caps = BackendCapabilities(
            read=True, write=True, delete=False, mkdir=True, readonly=False, versioning=True
        )

        repr_str = repr(caps)

        # Should be a string
        assert isinstance(repr_str, str)

        # Should contain class name
        assert "BackendCapabilities" in repr_str

        # Should contain some capability info
        assert "read=" in repr_str or "write=" in repr_str

    def test_str(self):
        """Test __str__ returns human-readable string."""
        caps = BackendCapabilities(read=True, write=True, delete=True)

        str_repr = str(caps)

        # Should be a string
        assert isinstance(str_repr, str)

        # Should be non-empty
        assert len(str_repr) > 0

    def test_capabilities_can_be_used_as_dict_keys(self):
        """Test that capabilities can be used as dictionary keys (requires __hash__)."""
        caps1 = BackendCapabilities(read=True, write=True)
        caps2 = BackendCapabilities(read=True, write=False)

        # Should be usable as dict keys
        capability_dict = {caps1: "read-write", caps2: "read-only"}

        assert capability_dict[caps1] == "read-write"
        assert capability_dict[caps2] == "read-only"

    def test_capabilities_in_set(self):
        """Test that capabilities can be added to sets (requires __hash__ and __eq__)."""
        caps1 = BackendCapabilities(read=True, write=True)
        caps2 = BackendCapabilities(read=True, write=True)  # Same as caps1
        caps3 = BackendCapabilities(read=True, write=False)

        capability_set = {caps1, caps2, caps3}

        # caps1 and caps2 are equal, so set should have 2 items
        assert len(capability_set) == 2

    def test_str_basic_operations(self):
        """Test __str__ with only basic operations."""
        caps = BackendCapabilities()  # All defaults
        result = str(caps)
        assert result == "basic file operations"

    def test_str_with_versioning(self):
        """Test __str__ includes versioning."""
        caps = BackendCapabilities(versioning=True)
        result = str(caps)
        assert "versioning" in result

    def test_str_with_metadata(self):
        """Test __str__ includes metadata."""
        caps = BackendCapabilities(metadata=True)
        result = str(caps)
        assert "metadata" in result

    def test_str_with_presigned_urls(self):
        """Test __str__ includes presigned URLs."""
        caps = BackendCapabilities(presigned_urls=True)
        result = str(caps)
        assert "presigned URLs" in result

    def test_str_with_copy_optimization(self):
        """Test __str__ includes server-side copy."""
        caps = BackendCapabilities(copy_optimization=True)
        result = str(caps)
        assert "server-side copy" in result

    def test_str_with_hash_on_metadata(self):
        """Test __str__ includes fast hashing."""
        caps = BackendCapabilities(hash_on_metadata=True)
        result = str(caps)
        assert "fast hashing" in result

    def test_str_with_symbolic_links(self):
        """Test __str__ includes symbolic links."""
        caps = BackendCapabilities(symbolic_links=True)
        result = str(caps)
        assert "symbolic links" in result

    def test_str_with_readonly(self):
        """Test __str__ includes read-only."""
        caps = BackendCapabilities(readonly=True)
        result = str(caps)
        assert "read-only" in result

    def test_str_with_temporary(self):
        """Test __str__ includes temporary storage."""
        caps = BackendCapabilities(temporary=True)
        result = str(caps)
        assert "temporary storage" in result

    def test_str_with_multiple_features(self):
        """Test __str__ with multiple features."""
        caps = BackendCapabilities(versioning=True, metadata=True, readonly=True)
        result = str(caps)
        assert "versioning" in result
        assert "metadata" in result
        assert "read-only" in result
        # Should be comma-separated
        assert "," in result
