# Copyright (c) 2025 Softwell Srl, Milano, Italy
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Temporary local decorators - will be replaced by genro_core.decorators when available."""


def apiready(obj_or_path=None, **kwargs):
    """No-op decorator placeholder for @apiready from genro_core.

    This is a temporary implementation that does nothing. It will be replaced
    by the actual decorator from genro_core.decorators.api when available.

    Usage:
        @apiready
        def method(self):
            pass

        @apiready(path="/storage")
        class MyClass:
            pass
    """
    def decorator(obj):
        return obj

    # If called without arguments (@apiready), obj_or_path is the decorated object
    if callable(obj_or_path):
        return obj_or_path

    # If called with arguments (@apiready(path="...")), return the decorator
    return decorator
