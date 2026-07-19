# new-wokers external worker patch record

This branch enables the optimized BLACS `post_experiment` state for the two
workers used by the multishot timing test.

The two workers are loaded from the labscript runtime configuration, not from
this BLACS repository. Their installed locations are therefore recorded here
so the branch has an auditable and reversible description of the change.

## Active locations

- `C:\Users\RoyTest\labscript-suite\userlib\user_devices\SpectrumAWG\blacs_workers.py`
- `C:\Users\RoyTest\.conda\envs\labscript-dev\Lib\site-packages\labscript_devices\PulseBlaster_No_DDS.py`

The `base` environment is intentionally unchanged. The PulseBlaster file in
`labscript-dev` was first made independent because Conda had hard-linked it to
the corresponding file in `base`.

## Added worker methods

SpectrumAWG:

```python
def post_experiment(self):
    return True
```

PulseBlaster:

```python
def post_experiment(self):
    return self.transition_to_manual()
```

The PulseBlaster method preserves its existing end-of-shot and wait checks.
For the last queued shot, BLACS still calls `transition_to_manual()` as part of
the normal final cleanup. To revert either change, remove only its marked
`CODEX CHANGE START` through `CODEX CHANGE END` block.
