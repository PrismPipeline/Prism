"""
 -----------------------------------------------------------------------------
 Copyright (c) 2009-2017, Shotgun Software Inc

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions are met:

  - Redistributions of source code must retain the above copyright notice, this
    list of conditions and the following disclaimer.

  - Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution.

  - Neither the name of the Shotgun Software Inc nor the names of its
    contributors may be used to endorse or promote products derived from this
    software without specific prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

-----------------------------------------------------------------------------
"""

from ..six.moves import cPickle as pickle
import os

from .errors import MockgunError


class SchemaFactory(object):
    """
    Allows to instantiate a pickled schema.
    """

    _schema_entity_cache = None
    _schema_entity_cache_path = None
    _schema_cache = None
    _schema_cache_path = None

    @classmethod
    def get_schemas(cls, schema_path, schema_entity_path):
        """
        Retrieves the schemas from disk.

        :param str schema_path: Path to the schema.
        :param str schema_entity_path: Path to the entities schema.

        :returns: Pair of dictionaries holding the schema and entities schema.
        :rtype: tuple
        """
        if not os.path.exists(schema_path):
            raise MockgunError("Cannot locate Mockgun schema file '%s'!" % schema_path)

        if not os.path.exists(schema_entity_path):
            raise MockgunError("Cannot locate Mockgun schema file '%s'!" % schema_entity_path)

        # Poor man's attempt at a cache. All of our use cases deal with a single pair of files
        # for the duration of the unit tests, so keep a cache for both inputs. We don't want
        # to deal with ever growing caches anyway. Just having this simple cache has shown
        # speed increases of up to 500% for Toolkit unit tests alone.

        if schema_path != cls._schema_cache_path:
            cls._schema_cache = cls._read_file(schema_path)
            cls._schema_cache_path = schema_path

        if schema_entity_path != cls._schema_entity_cache_path:
            cls._schema_entity_cache = cls._read_file(schema_entity_path)
            cls._schema_entity_cache_path = schema_entity_path

        return cls._schema_cache, cls._schema_entity_cache

    @classmethod
    def _read_file(cls, path):
        fh = open(path, "rb")
        try:
            return pickle.load(fh)
        finally:
            fh.close()


# Highest protocol that Python 2.4 supports, which is the earliest version of Python we support.
# Actually, this is the same version that Python 2.7 supports at the moment!
_HIGHEST_24_PICKLE_PROTOCOL = 2


# ----------------------------------------------------------------------------
# Utility methods
def generate_schema(shotgun, schema_file_path, schema_entity_file_path):
    """
    Helper method for mockgun.
    Generates the schema files needed by the mocker by connecting to a real shotgun
    and downloading the schema information for that site. Once the generated schema
    files are being passed to mockgun, it will mimic the site's schema structure.

    :param sg_url: Shotgun site url
    :param sg_script: Script name to connect with
    :param sg_key: Script key to connect with
    :param schema_file_path: Path where to write the main schema file to
    :param schema_entity_file_path: Path where to write the entity schema file to
    """

    schema = shotgun.schema_read()
    fh = open(schema_file_path, "wb")
    try:
        pickle.dump(schema, fh, protocol=_HIGHEST_24_PICKLE_PROTOCOL)
    finally:
        fh.close()

    schema_entity = shotgun.schema_entity_read()
    fh = open(schema_entity_file_path, "wb")
    try:
        pickle.dump(schema_entity, fh, protocol=_HIGHEST_24_PICKLE_PROTOCOL)
    finally:
        fh.close()
