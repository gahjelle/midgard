"""A Dataset time field
"""
# Standard library imports
from datetime import timedelta

# Midgard imports
from midgard.data.fieldtypes._fieldtype import FieldType
from midgard.data.time import TimeDelta, TimeDeltaArray
from midgard.dev import exceptions
from midgard.dev import plugins


@plugins.register
class TimeDeltaField(FieldType):

    _factory = staticmethod(TimeDelta)

    def _post_init(self, val, **field_args):
        """Initialize time field"""
        if isinstance(val, TimeDeltaArray):
            data = val
        else:
            try:
                scale = field_args.pop("scale")
            except KeyError:
                raise exceptions.InitializationError(
                    f"{self._factory.__name__}() missing 1 required positional argument: 'scale'"
                ) from None

            try:
                fmt = field_args.pop("fmt")
            except KeyError:
                raise exceptions.InitializationError(
                    f"{self._factory.__name__}() missing 1 required positional argument: 'fmt'"
                ) from None

            data = self._factory(val, scale, fmt, **field_args)

        # Check that unit is not given, overwrite with time scale
        if self._unit is not None:
            raise exceptions.InitializationError("Parameter 'unit' should not be specified for times")
        self._unit = None

        # Check that the correct number of observations are given
        if len(data) != self.num_obs:
            raise ValueError(f"{self.name!r} initialized with {len(data)} values, expected {self.num_obs}")

        # Store the data as a TimeDeltaArray
        self.data = data

    def plot_values(self, field=None):
        """Return values of the field in a form that can be plotted"""
        if not field:
            return self.data.timedelta

        values = getattr(self.data, field)
        if isinstance(values, TimeDeltaArray):
            return values.timedelta
        else:
            return values

    def _prepend_empty(self, num_obs, memo):
        empty = TimeDelta([timedelta(seconds=0)] * num_obs, scale="utc", fmt="timedelta")
        empty_id = id(empty)
        self.data = TimeDeltaArray.insert(self.data, 0, empty, memo)
        memo.pop(empty_id, None)

    def _append_empty(self, num_obs, memo):
        empty = TimeDelta([timedelta(seconds=0)] * num_obs, scale="utc", fmt="timedelta")
        empty_id = id(empty)
        self.data = TimeDeltaArray.insert(self.data, self.num_obs, empty, memo)
        memo.pop(empty_id, None)

    def _subset(self, idx, memo):
        self.data = self.data.subset(idx, memo)

    def _extend(self, other_field, memo) -> None:
        """Add observations from another field"""
        if other_field.data.ndim != self.data.ndim:
            raise ValueError(
                f"Field '{self.name}' cannot be extended. Dimensions must be equal. ({other_field.data.ndim} != {self.data.ndim})"
            )

        self.data = TimeDeltaArray.insert(self.data, self.num_obs, other_field.data, memo)

    @classmethod
    def _read(cls, h5_group, memo) -> "TimeField":
        """Read a TimeField from a HDF5 data source"""
        name = h5_group.attrs["fieldname"]
        if name in memo:
            time = memo[name]
        else:
            time = TimeDeltaArray._read(h5_group, memo)
        return cls(num_obs=len(time), name=name.split(".")[-1], val=time)

    def _write(self, h5_group, memo) -> None:
        """Write a TimeField to a HDF5 data source"""
        self.data._write(h5_group, memo)
