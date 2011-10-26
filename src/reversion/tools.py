
from django.db import IntegrityError


def recursive_revert(versions):
    """
       required argument: versions, a list of versions to revert
    
       attempt to revert each of the list of versions. Expect and handle IntegrityErrors if the versions depend on each other. 

       raises RevertError if there are circular dependencies
    """
    from models import RevertError
    unreverted_versions = []
    for version in versions:
        try:
            version.revert()
        except IntegrityError:
            unreverted_versions.append(version)
    if len(unreverted_versions) == len(versions):
        raise RevertError("Could not revert revision, due to database integrity errors.")
    if unreverted_versions:
        recursive_revert(unreverted_versions)

