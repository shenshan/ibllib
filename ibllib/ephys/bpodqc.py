import os
from pathlib import Path, PureWindowsPath

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import interpolate

import ibllib.io.raw_data_loaders as raw
import ibllib.plots as plots
from ibllib.ephys.ephysqc import _qc_from_path
from ibllib.ephys.oneutils import uuid_to_path
from ibllib.io.extractors.training_trials import (get_choice,
                                                  get_feedback_times,
                                                  get_feedbackType,
                                                  get_goCueOnset_times,
                                                  get_goCueTrigger_times,
                                                  get_intervals,
                                                  get_port_events,
                                                  get_response_times,
                                                  get_stimOn_times,
                                                  get_stimOnTrigger_times)
from oneibl.one import ONE

one = ONE()


@uuid_to_path(dl=True)
def get_bpod_fronts(session_path, save=False, data=False, settings=False):
    if not data:
        data = raw.load_data(session_path)
    if not settings:
        settings = raw.load_settings(session_path)
    if settings is None:
        settings = {"IBLRIG_VERSION_TAG": "100.0.0"}
    elif settings["IBLRIG_VERSION_TAG"] == "":
        settings.update({"IBLRIG_VERSION_TAG": "100.0.0"})

    BNC1_fronts = np.array([[np.nan, np.nan]])
    BNC2_fronts = np.array([[np.nan, np.nan]])
    for tr in data:
        BNC1_fronts = np.append(
            BNC1_fronts,
            np.array(
                [
                    [x, 1]
                    for x in tr["behavior_data"]["Events timestamps"].get("BNC1High", [np.nan])
                ]
            ),
            axis=0,
        )
        BNC1_fronts = np.append(
            BNC1_fronts,
            np.array(
                [
                    [x, -1]
                    for x in tr["behavior_data"]["Events timestamps"].get("BNC1Low", [np.nan])
                ]
            ),
            axis=0,
        )
        BNC2_fronts = np.append(
            BNC2_fronts,
            np.array(
                [
                    [x, 1]
                    for x in tr["behavior_data"]["Events timestamps"].get("BNC2High", [np.nan])
                ]
            ),
            axis=0,
        )
        BNC2_fronts = np.append(
            BNC2_fronts,
            np.array(
                [
                    [x, -1]
                    for x in tr["behavior_data"]["Events timestamps"].get("BNC2Low", [np.nan])
                ]
            ),
            axis=0,
        )

    BNC1_fronts = BNC1_fronts[1:, :]
    BNC1_fronts = BNC1_fronts[BNC1_fronts[:, 0].argsort()]
    BNC2_fronts = BNC2_fronts[1:, :]
    BNC2_fronts = BNC2_fronts[BNC2_fronts[:, 0].argsort()]

    BNC1 = {"times": BNC1_fronts[:, 0], "polarities": BNC1_fronts[:, 1]}
    BNC2 = {"times": BNC2_fronts[:, 0], "polarities": BNC2_fronts[:, 1]}

    return [BNC1, BNC2]


# --------------------------------------------------------------------------- #
@uuid_to_path(dl=True)
def get_trial_type(session_path, save=False, data=False, settings=False):
    if not data:
        data = raw.load_data(session_path)
    if not settings:
        settings = raw.load_settings(session_path)
    if settings is None:
        settings = {"IBLRIG_VERSION_TAG": "100.0.0"}
    elif settings["IBLRIG_VERSION_TAG"] == "":
        settings.update({"IBLRIG_VERSION_TAG": "100.0.0"})

    trial_type = []
    for tr in data:
        if ~np.isnan(tr["behavior_data"]["States timestamps"]['reward'][0][0]):
            trial_type.append(1)
        elif ~np.isnan(tr["behavior_data"]["States timestamps"]['error'][0][0]):
            trial_type.append(-1)
        elif ~np.isnan(tr["behavior_data"]["States timestamps"]['no_go'][0][0]):
            trial_type.append(0)
        else:
            print("trial is not in {-1, 0, 1}")
            trial_type.append(np.nan)

    trial_type = np.array(trial_type)

    if raw.save_bool(save, "_ibl_trials.type.npy"):
        lpath = os.path.join(session_path, "alf", "_ibl_trials.type.npy")
        np.save(lpath, trial_type)

    return trial_type


@uuid_to_path(dl=True)
def get_itiIn_times(session_path, save=False, data=False, settings=False):
    if not data:
        data = raw.load_data(session_path)
    if not settings:
        settings = raw.load_settings(session_path)
    if settings is None:
        settings = {"IBLRIG_VERSION_TAG": "100.0.0"}
    elif settings["IBLRIG_VERSION_TAG"] == "":
        settings.update({"IBLRIG_VERSION_TAG": "100.0.0"})

    itiIn_times = np.array(
        [tr["behavior_data"]["States timestamps"]["exit_state"][0][0] for tr in data]
    )

    if raw.save_bool(save, "_ibl_trials.itiIn_times.npy"):
        lpath = os.path.join(session_path, "alf", "_ibl_trials.itiIn_times.npy")
        np.save(lpath, itiIn_times)

    return itiIn_times


@uuid_to_path(dl=True)
def get_stimFreezeTrigger_times(session_path, save=False, data=False, settings=False):
    if not data:
        data = raw.load_data(session_path)
    if not settings:
        settings = raw.load_settings(session_path)
    if settings is None:
        settings = {"IBLRIG_VERSION_TAG": "100.0.0"}
    elif settings["IBLRIG_VERSION_TAG"] == "":
        settings.update({"IBLRIG_VERSION_TAG": "100.0.0"})

    freeze_reward = np.array(
        [
            True
            if np.all(~np.isnan(tr["behavior_data"]["States timestamps"]["freeze_reward"][0]))
            else False
            for tr in data
        ]
    )
    freeze_error = np.array(
        [
            True
            if np.all(~np.isnan(tr["behavior_data"]["States timestamps"]["freeze_error"][0]))
            else False
            for tr in data
        ]
    )
    no_go = np.array(
        [
            True
            if np.all(~np.isnan(tr["behavior_data"]["States timestamps"]["no_go"][0]))
            else False
            for tr in data
        ]
    )
    assert np.sum(freeze_error) + np.sum(freeze_reward) + np.sum(no_go) == len(data)

    stimFreezeTrigger = np.array([])
    for r, e, n, tr in zip(freeze_reward, freeze_error, no_go, data):
        if n:
            stimFreezeTrigger = np.append(stimFreezeTrigger, np.nan)
            continue
        state = "freeze_reward" if r else "freeze_error"
        stimFreezeTrigger = np.append(
            stimFreezeTrigger, tr["behavior_data"]["States timestamps"][state][0][0]
        )

    if raw.save_bool(save, "_ibl_trials.stimFreeze_times.npy"):
        lpath = os.path.join(session_path, "alf", "_ibl_trials.stimFreeze_times.npy")
        np.save(lpath, stimFreezeTrigger)

    return stimFreezeTrigger


@uuid_to_path(dl=True)
def get_stimOffTrigger_times(session_path, save=False, data=False, settings=False):
    if not data:
        data = raw.load_data(session_path)
    if not settings:
        settings = raw.load_settings(session_path)
    if settings is None:
        settings = {"IBLRIG_VERSION_TAG": "100.0.0"}
    elif settings["IBLRIG_VERSION_TAG"] == "":
        settings.update({"IBLRIG_VERSION_TAG": "100.0.0"})

    stimOffTrigger_times = np.array(
        [tr["behavior_data"]["States timestamps"]["hide_stim"][0][0] for tr in data]
    )
    no_goTrigger_times = np.array(
        [tr["behavior_data"]["States timestamps"]["no_go"][0][0] for tr in data]
    )
    # Stim off trigs are either in their own state or in the no_go state if the mouse did not move
    assert all(~np.isnan(no_goTrigger_times) == np.isnan(stimOffTrigger_times))
    stimOffTrigger_times[~np.isnan(no_goTrigger_times)] = no_goTrigger_times[
        ~np.isnan(no_goTrigger_times)
    ]

    if raw.save_bool(save, "_ibl_trials.stimOffTrigger_times.npy"):
        lpath = Path(session_path).joinpath("alf", "_ibl_trials.stimOffTrigger_times.npy")
        np.save(lpath, stimOffTrigger_times)

    return stimOffTrigger_times


@uuid_to_path(dl=True)
def get_stimOff_times_from_state(session_path, save=False, data=False, settings=False):
    """ Will return NaN is trigger state == 0.1 secs
    """

    if not data:
        data = raw.load_data(session_path)
    if not settings:
        settings = raw.load_settings(session_path)
    if settings is None:
        settings = {"IBLRIG_VERSION_TAG": "100.0.0"}
    elif settings["IBLRIG_VERSION_TAG"] == "":
        settings.update({"IBLRIG_VERSION_TAG": "100.0.0"})

    hide_stim_state = np.array(
        [tr["behavior_data"]["States timestamps"]["hide_stim"][0] for tr in data]
    )
    stimOff_times = np.array([])
    for s in hide_stim_state:
        x = s[0] - s[1]
        if np.isnan(x) or np.abs(x) > 0.0999:
            stimOff_times = np.append(stimOff_times, np.nan)
        else:
            stimOff_times = np.append(stimOff_times, s[1])

    if raw.save_bool(save, "_ibl_trials.stimOff_times.npy"):
        lpath = Path(session_path).joinpath("alf", "_ibl_trials.stimOff_times.npy")
        np.save(lpath, stimOff_times)

    return stimOff_times


@uuid_to_path(dl=True)
def get_stimOnOffFreeze_times_from_BNC1(session_path, save=False, data=False, settings=False):
    """Get stim onset offset and freeze using the FPGA specifications"""
    if not data:
        data = raw.load_data(session_path)
    if not settings:
        settings = raw.load_settings(session_path)
    if settings is None:
        settings = {"IBLRIG_VERSION_TAG": "100.0.0"}
    elif settings["IBLRIG_VERSION_TAG"] == "":
        settings.update({"IBLRIG_VERSION_TAG": "100.0.0"})

    choice = get_choice(session_path, data=data, settings=settings)
    f2TTL = [get_port_events(tr, name="BNC1") for tr in data]
    stimOn_times = np.array([])
    stimOff_times = np.array([])
    stimFreeze_times = np.array([])

    for tr in f2TTL:
        if tr and len(tr) >= 2:
            # 2nd order criteria:
            # stimOn -> Closest one to stimOnTrigger?
            # stimOff -> Closest one to stimOffTrigger?
            # stimFreeze -> Closest one to stimFreezeTrigger?
            stimOn_times = np.append(stimOn_times, tr[0])
            stimOff_times = np.append(stimOff_times, tr[-1])
            stimFreeze_times = np.append(stimFreeze_times, tr[-2])
        else:
            stimOn_times = np.append(stimOn_times, np.nan)
            stimOff_times = np.append(stimOff_times, np.nan)
            stimFreeze_times = np.append(stimFreeze_times, np.nan)

    # In no_go trials no stimFreeze happens jsut stim Off
    stimFreeze_times[choice == 0] = np.nan

    if raw.save_bool(save, "_ibl_trials.stimOn_times.npy"):
        lpath = Path(session_path).joinpath("alf", "_ibl_trials.stimOn_times.npy")
        np.save(lpath, stimOn_times)
    if raw.save_bool(save, "_ibl_trials.stimOff_times.npy"):
        lpath = Path(session_path).joinpath("alf", "_ibl_trials.stimOff_times.npy")
        np.save(lpath, stimOff_times)
    if raw.save_bool(save, "_ibl_trials.stimFreeze_times.npy"):
        lpath = Path(session_path).joinpath("alf", "_ibl_trials.stimFreeze_times.npy")
        np.save(lpath, stimFreeze_times)

    return stimOn_times, stimOff_times, stimFreeze_times


@uuid_to_path(dl=True)
def get_bonsai_screen_data(session_path, save=False, data=False, settings=False):
    if not data:
        data = raw.load_data(session_path)
    if not settings:
        settings = raw.load_settings(session_path)
    if settings is None:
        settings = {"IBLRIG_VERSION_TAG": "100.0.0"}
    elif settings["IBLRIG_VERSION_TAG"] == "":
        settings.update({"IBLRIG_VERSION_TAG": "100.0.0"})
    path = Path(session_path).joinpath("raw_behavior_data", "_iblrig_stimPositionScreen.raw.csv")
    screen_data = pd.read_csv(path, sep=" ", header=None)

    return screen_data


@uuid_to_path(dl=True)
def get_bonsai_sync_square_update_times(session_path, save=False, data=False, settings=False):
    if not data:
        data = raw.load_data(session_path)
    if not settings:
        settings = raw.load_settings(session_path)
    if settings is None:
        settings = {"IBLRIG_VERSION_TAG": "100.0.0"}
    elif settings["IBLRIG_VERSION_TAG"] == "":
        settings.update({"IBLRIG_VERSION_TAG": "100.0.0"})

    path = Path(session_path).joinpath("raw_behavior_data", "_iblrig_syncSquareUpdate.raw.csv")
    if path.exists():
        sync_square_update_times = pd.read_csv(path, sep=",", header=None)
        return sync_square_update_times

    return


@uuid_to_path(dl=True)
def get_errorCueTrigger_times(session_path, save=False, data=False, settings=False):
    if not data:
        data = raw.load_data(session_path)
    if not settings:
        settings = raw.load_settings(session_path)
    if settings is None:
        settings = {"IBLRIG_VERSION_TAG": "100.0.0"}
    elif settings["IBLRIG_VERSION_TAG"] == "":
        settings.update({"IBLRIG_VERSION_TAG": "100.0.0"})

    errorCueTrigger_times = np.zeros(len(data)) * np.nan

    for i, tr in enumerate(data):
        nogo = tr["behavior_data"]["States timestamps"]["no_go"][0][0]
        error = tr["behavior_data"]["States timestamps"]["error"][0][0]
        if np.all(~np.isnan(nogo)):
            errorCueTrigger_times[i] = nogo
        elif np.all(~np.isnan(error)):
            errorCueTrigger_times[i] = error

    return errorCueTrigger_times


@uuid_to_path(dl=True)
def _get_trimmed_data_from_pregenerated_files(
    session_path, save=False, data=False, settings=False
):
    """Extracts positions, contrasts, quiescent delay, stimulus phase and probability left
    from pregenerated session files.
    Optional: saves alf contrastLR and probabilityLeft npy files"""
    if not data:
        data = raw.load_data(session_path)
    if not settings:
        settings = raw.load_settings(session_path)
    if settings is None:
        settings = {"IBLRIG_VERSION_TAG": "100.0.0"}
    elif settings["IBLRIG_VERSION_TAG"] == "":
        settings.update({"IBLRIG_VERSION_TAG": "100.0.0"})
    num = settings.get("PRELOADED_SESSION_NUM", None)
    if num is None:
        num = settings.get("PREGENERATED_SESSION_NUM", None)
    if num is None:
        fn = settings.get("SESSION_LOADED_FILE_PATH", None)
        fn = PureWindowsPath(fn).name
        num = "".join([d for d in fn if d.isdigit()])
        if num == "":
            raise ValueError("Can't extract left probability behaviour.")
    # Load the pregenerated file
    sessions_folder = Path(raw.__file__).parent.joinpath("extractors", "ephys_sessions")
    fname = f"session_{num}_ephys_pcqs.npy"
    pcqsp = np.load(sessions_folder.joinpath(fname))
    pos = pcqsp[:, 0]
    con = pcqsp[:, 1]
    pos = pos[: len(data)]
    con = con[: len(data)]
    contrastRight = con.copy()
    contrastLeft = con.copy()
    contrastRight[pos < 0] = np.nan
    contrastLeft[pos > 0] = np.nan
    qui = pcqsp[:, 2]
    qui = qui[: len(data)]
    phase = pcqsp[:, 3]
    phase = phase[: len(data)]
    pLeft = pcqsp[:, 4]
    pLeft = pLeft[: len(data)]

    if raw.save_bool(save, "_ibl_trials.contrastLeft.npy"):
        lpath = os.path.join(session_path, "alf", "_ibl_trials.contrastLeft.npy")
        np.save(lpath, contrastLeft)

    if raw.save_bool(save, "_ibl_trials.contrastRight.npy"):
        rpath = os.path.join(session_path, "alf", "_ibl_trials.contrastRight.npy")
        np.save(rpath, contrastRight)

    if raw.save_bool(save, "_ibl_trials.probabilityLeft.npy"):
        lpath = Path(session_path).joinpath("alf", "_ibl_trials.probabilityLeft.npy")
        np.save(lpath, pLeft)

    return {
        "position": pos,
        "contrast": con,
        "quiescence": qui,
        "phase": phase,
        "prob_left": pLeft,
    }


@uuid_to_path(dl=True)
def load_bpod_data(session_path, fpga_time=False):
    """Extracts and loads ephys sessions from bpod data"""
    print(session_path)
    data = raw.load_data(session_path)
    settings = raw.load_settings(session_path)
    stimOn_times, stimOff_times, stimFreeze_times = get_stimOnOffFreeze_times_from_BNC1(
        session_path
    )

    out = {
        "position": None,
        "contrast": None,
        "quiescence": None,
        "phase": None,
        "prob_left": None,
        "choice": get_choice(session_path, save=False, data=data, settings=settings),
        "feedbackType": get_feedbackType(session_path, save=False, data=data, settings=settings),
        "correct": None,
        "intervals": get_intervals(session_path, save=False, data=data, settings=settings),
        "stimOnTrigger_times": get_stimOnTrigger_times(
            session_path, save=False, data=data, settings=settings
        ),
        "stimOn_times": stimOn_times,
        "stimOn_times_training": get_stimOn_times(
            session_path, save=False, data=data, settings=settings
        ),
        "stimOffTrigger_times": get_stimOffTrigger_times(
            session_path, save=False, data=data, settings=settings
        ),
        "stimOff_times": stimOff_times,
        "stimOff_times_from_state": get_stimOff_times_from_state(
            session_path, save=False, data=data, settings=settings
        ),
        "stimFreezeTrigger_times": get_stimFreezeTrigger_times(
            session_path, save=False, data=data, settings=settings
        ),
        "stimFreeze_times": stimFreeze_times,
        "goCueTrigger_times": get_goCueTrigger_times(
            session_path, save=False, data=data, settings=settings
        ),
        "goCue_times": get_goCueOnset_times(
            session_path, save=False, data=data, settings=settings
        ),
        "errorCueTrigger_times": get_errorCueTrigger_times(
            session_path, save=False, data=data, settings=settings
        ),
        "errorCue_times": None,
        "valveOpen_times": None,
        "response_times": get_response_times(
            session_path, save=False, data=data, settings=settings
        ),
        "feedback_times": get_feedback_times(
            session_path, save=False, data=data, settings=settings
        ),
        "itiIn_times": get_itiIn_times(session_path, save=False, data=data, settings=settings),
        "intervals_0": None,
        "intervals_1": None,
    }
    out.update(
        _get_trimmed_data_from_pregenerated_files(
            session_path, save=False, data=data, settings=settings
        )
    )
    # get valve_time and errorCue_times from feedback_times
    correct = np.sign(out["position"]) + np.sign(out["choice"]) == 0
    errorCue_times = out["feedback_times"].copy()
    valveOpen_times = out["feedback_times"].copy()
    errorCue_times[correct] = np.nan
    valveOpen_times[~correct] = np.nan
    out.update(
        {"errorCue_times": errorCue_times, "valveOpen_times": valveOpen_times, "correct": correct}
    )
    # split intervals
    out["intervals_0"] = out["intervals"][:, 0]
    out["intervals_1"] = out["intervals"][:, 1]
    _ = out.pop('intervals')
    if fpga_time:
        bpod2fpga = get_bpod2fpga_times_func(session_path)
        for k in out:
            if '_times' in k or 'intervals' in k:
                out[k] = bpod2fpga(out[k])
    return out


@uuid_to_path(dl=True)
def get_bpodqc_frame(session_path, qc_frame_only=False):
    """loads/extracts data from bpod raw files and appends computed qc variables to data frame
    optional returns only qc_frame"""
    bpod = load_bpod_data(session_path)

    GOCUE_STIMON_DELAY = 0.01  # -> 0.1
    FEEDBACK_STIMFREEZE_DELAY = 0.01  # -> 0.1
    VALVE_STIM_OFF_DELAY = 1
    VALVE_STIM_OFF_JITTER = 0.1
    ITI_IN_STIM_OFF_JITTER = 0.1
    ERROR_STIM_OFF_DELAY = 2
    ERROR_STIM_OFF_JITTER = 0.1  # -> 0.2
    RESPONSE_FEEDBACK_DELAY = 0.0005

# get from qccriteria.py (create!)
    qc_frame = {
        "nDatasetTypes": float,  # (Point 17)
        "intervals": float,  # (Point 18)
        "stimOnTrigger_times": float,  # (Point 19)
        "stimOn_times": float,  # (Point 20)
        "goCueTrigger_times": float,  # (Point 21)
        "goCue_times": float,  # (Point 22)
        "response_times": float,  # (Point 23)
        "feedback_times": float,  # (Point 24)
        "goCue_delays": float,  # (Point 25)
        "errorCue_delays": float,  # (Point 26)
        "stimOn_delays": float,  # (Point 27)
        "stimOff_delays": float,  # (Point 28)
        "stimFreeze_delays": float,  # (Point 29)
        "stimOn_goCue_delays": float,  # (Point 1)
        "response_feedback_delays": float,  # (Point 2)
        "response_stimFreeze_delays": float,  # (Point 3)
        "stimOff_itiIn_delays": float,  # (Point 4)
        "wheel_freeze_during_quiescence": float,  # (Point 5)
        "wheel_move_before_feedback": float,  # (Point 6)
        "stimulus_move_before_goCue": float,  # (Point 7)
        "positive_feedback_stimOff_delays": float,  # (Point 8)
        "negative_feedback_stimOff_delays": float,  # (Point 9)
        "valve_pre_trial": float,  # (Point 11)
        "audio_pre_trial": float,  # (Point 12)
        "trial_event_sequence_error": float,  # (Point 13)
        "trial_event_sequence_correct": float,  # (Point 14)
        "trial_length": float,  # (Point 15)
    }

    qc_frame = {
        "n_feedback": np.int32(
            ~np.isnan(bpod["valveOpen_times"]) + ~np.isnan(bpod["errorCue_times"])
        ),
        "stimOn_times_nan": ~np.isnan(bpod["stimOn_times"]),
        "goCue_times_nan": ~np.isnan(bpod["goCue_times"]),
        "stimOn_times_before_goCue_times": bpod["goCue_times"] - bpod["stimOn_times"] > 0,
        "stimOn_times_goCue_times_delay": (
            np.abs(bpod["goCue_times"] - bpod["stimOn_times"]) <= GOCUE_STIMON_DELAY
        ),
        "stim_freeze_before_feedback": bpod["feedback_times"] - bpod["stimFreeze_times"] > 0,
        "stim_freeze_feedback_delay": (
            np.abs(bpod["feedback_times"] - bpod["stimFreeze_times"]) <= FEEDBACK_STIMFREEZE_DELAY
        ),
        "stimOff_delay_valve": np.less(
            np.abs(bpod["stimOff_times"] - bpod["valveOpen_times"] - VALVE_STIM_OFF_DELAY),
            VALVE_STIM_OFF_JITTER,
            out=np.ones(len(bpod["stimOn_times"]), dtype=np.bool),
            where=~np.isnan(bpod["valveOpen_times"]),
        ),
        "iti_in_delay_stim_off": np.less(
            np.abs(bpod["stimOff_times"] - bpod["itiIn_times"]),
            ITI_IN_STIM_OFF_JITTER,
            out=np.ones(len(bpod["stimOn_times"]), dtype=np.bool),
            where=~np.isnan(bpod["errorCue_times"]),
        ),  # FIXME: where= is wrong, no_go trials have a error tone but longer delay!
        "stimOff_delay_noise": np.less(
            np.abs(bpod["stimOff_times"] - bpod["errorCue_times"] - ERROR_STIM_OFF_DELAY),
            ERROR_STIM_OFF_JITTER,
            out=np.ones(len(bpod["stimOn_times"]), dtype=np.bool),
            where=~np.isnan(bpod["errorCue_times"]),
        ),
        "response_times_nan": ~np.isnan(bpod["response_times"]),
        "response_times_increase": np.diff(np.append([0], bpod["response_times"])) > 0,
        "response_times_goCue_times_diff": bpod["response_times"] - bpod["goCue_times"] > 0,
        "response_before_feedback": bpod["feedback_times"] - bpod["response_times"] > 0,
        "response_feedback_delay": (
            bpod["feedback_times"] - bpod["response_times"] < RESPONSE_FEEDBACK_DELAY
        ),
    }
    bpodqc_frame = bpod.copy()
    bpodqc_frame.update(qc_frame)
    bpodqc_frame = pd.DataFrame.from_dict(bpodqc_frame)
    return bpodqc_frame if not qc_frame_only else qc_frame


# --------------------------------------------------------------------------- #
@uuid_to_path(dl=True)
def check_iti_stimOffTrig(session_path):
    bpod = load_bpod_data(session_path)

    iti_stimOff_diff = bpod["stimOffTrigger_times"] - bpod["itiIn_times"]
    # 0.1 means that stimOff lasted more than 0.1 to go off.or BNC1 was not detected
    # 2 sec means it was a no go trial and the trig was at the beginning of the no_go state
    # that lasts for 2 sec after which itiState enters
    return iti_stimOff_diff


@uuid_to_path(dl=True)
def check_feedback_stim_off_delay(session_path):
    bpod = load_bpod_data(session_path)

    valve_stim_off_diff = bpod["feedback_times"] - bpod["stimOffTrigger_times"]

    return valve_stim_off_diff


# --------------------------------------------------------------------------- #
@uuid_to_path(dl=True)
def count_qc_failures(session_path):
    fpgaqc_frame = _qc_from_path(session_path, display=True)
    bpodqc_frame = get_bpodqc_frame(session_path)
    qc_fields = [
        "n_feedback",
        "stimOn_times_nan",
        "goCue_times_nan",
        "stimOn_times_before_goCue_times",
        "stimOn_times_goCue_times_delay",
        "stim_freeze_before_feedback",
        "stim_freeze_feedback_delay",
        "stimOff_delay_valve",
        "iti_in_delay_stim_off",
        "stimOff_delay_noise",
        "response_times_nan",
        "response_times_increase",
        "response_times_goCue_times_diff",
    ]
    for k in qc_fields:
        print("FPGA nFailed", k, ":", sum(np.bitwise_not(fpgaqc_frame[k])), len(fpgaqc_frame[k]))
        print("BPOD nFailed", k, ":", sum(np.bitwise_not(bpodqc_frame[k])), len(bpodqc_frame[k]))


@uuid_to_path(dl=True)
def plot_bpod_session(session_path, ax=None):
    if ax is None:
        f, ax = plt.subplots()
    bpodqc_frame = get_bpodqc_frame(session_path)
    BNC1, BNC2 = get_bpod_fronts(session_path)
    width = 0.5
    ymax = 5
    plots.squares(BNC1["times"], BNC1["polarities"] * 0.4 + 1, ax=ax, c="k")
    plots.squares(BNC2["times"], BNC2["polarities"] * 0.4 + 2, ax=ax, c="k")
    plots.vertical_lines(
        bpodqc_frame["goCueTrigger_times"],
        ymin=0,
        ymax=ymax,
        ax=ax,
        label="goCueTrigger_times",
        color="b",
        alpha=0.5,
        linewidth=width,
    )
    plots.vertical_lines(
        bpodqc_frame["goCue_times"],
        ymin=0,
        ymax=ymax,
        ax=ax,
        label="goCue_times",
        color="b",
        linewidth=width,
    )
    plots.vertical_lines(
        bpodqc_frame["intervals_0"],
        ymin=0,
        ymax=ymax,
        ax=ax,
        label="start_trial",
        color="m",
        linewidth=width,
    )
    plots.vertical_lines(
        bpodqc_frame["errorCueTrigger_times"],
        ymin=0,
        ymax=ymax,
        ax=ax,
        label="errorCueTrigger_times",
        color="r",
        alpha=0.5,
        linewidth=width,
    )
    plots.vertical_lines(
        bpodqc_frame["errorCue_times"],
        ymin=0,
        ymax=ymax,
        ax=ax,
        label="errorCue_times",
        color="r",
        linewidth=width,
    )
    plots.vertical_lines(
        bpodqc_frame["valveOpen_times"],
        ymin=0,
        ymax=ymax,
        ax=ax,
        label="valveOpen_times",
        color="g",
        linewidth=width,
    )
    plots.vertical_lines(
        bpodqc_frame["stimFreezeTrigger_times"],
        ymin=0,
        ymax=ymax,
        ax=ax,
        label="stimFreezeTrigger_times",
        color="k",
        alpha=0.5,
        linewidth=width,
    )
    plots.vertical_lines(
        bpodqc_frame["stimFreeze_times"],
        ymin=0,
        ymax=ymax,
        ax=ax,
        label="stimFreeze_times",
        color="y",
        linewidth=width,
    )
    plots.vertical_lines(
        bpodqc_frame["stimOffTrigger_times"],
        ymin=0,
        ymax=ymax,
        ax=ax,
        label="stimOffTrigger_times",
        color="c",
        alpha=0.5,
        linewidth=width,
    )
    plots.vertical_lines(
        bpodqc_frame["stimOff_times"],
        ymin=0,
        ymax=ymax,
        ax=ax,
        label="stimOff_times",
        color="c",
        linewidth=width,
    )
    plots.vertical_lines(
        bpodqc_frame["stimOnTrigger_times"],
        ymin=0,
        ymax=ymax,
        ax=ax,
        label="stimOnTrigger_times",
        color="tab:orange",
        alpha=0.5,
        linewidth=width,
    )
    plots.vertical_lines(
        bpodqc_frame["stimOn_times"],
        ymin=0,
        ymax=ymax,
        ax=ax,
        label="stimOn_times",
        color="tab:orange",
        linewidth=width,
    )
    ax.legend()
    ax.set_yticklabels(["", "f2ttl", "audio", ""])
    ax.set_yticks([0, 1, 2, 3])
    ax.set_ylim([0, 3])


@uuid_to_path(dl=True)
def get_bpod2fpga_times_func(session_path):
    session_path = Path(session_path)

    # Load bpod intervals
    data = raw.load_data(session_path)
    settings = raw.load_settings(session_path)
    bpod_intervals = get_intervals(session_path, save=False, data=data, settings=settings)
    # Load _ibl_trials.intervals.npy
    eid = one.eid_from_path(session_path)
    if eid is None:
        print(f"No session found with path = {session_path}")
        return
    fpga_intervals = one.load(eid, dataset_types='trials.intervals')
    if not fpga_intervals:
        print(f"tirals.intervals datasetType not found for session {eid}")
    else:
        fpga_intervals = fpga_intervals[0]
    # align
    bpod_tstarts, fpga_tstarts = raw.sync_trials_robust(bpod_intervals[:, 0], fpga_intervals[:, 0])
    # Generate interp func
    bpod2fpga = interpolate.interp1d(bpod_tstarts, fpga_tstarts, fill_value="extrapolate")

    return bpod2fpga


@uuid_to_path(dl=True)
def plot_session_trigger_response_diffs(session_path, ax=None):
    trigger_diffs = get_session_trigger_response_delays(session_path)

    sett = raw.load_settings(session_path)
    eid = one.eid_from_path(session_path)
    if ax is None:
        f, ax = plt.subplots()
    tit = f"{sett['SESSION_NAME']}: {eid}"
    ax.title.set_text(tit)
    ax.hist(trigger_diffs["goCue"], alpha=0.5, bins=50, label="goCue_diff")
    ax.hist(trigger_diffs["errorCue"], alpha=0.5, bins=50, label="errorCue_diff")
    ax.hist(trigger_diffs["stimOn"], alpha=0.5, bins=50, label="stimOn_diff")
    ax.hist(trigger_diffs["stimOff"], alpha=0.5, bins=50, label="stimOff_diff")
    ax.hist(trigger_diffs["stimFreeze"], alpha=0.5, bins=50, label="stimFreeze_diff")
    ax.legend(loc="best")


@uuid_to_path(dl=True)
def get_session_trigger_response_delays(session_path):
    bpod = load_bpod_data(session_path)
    # get diff from triggers to detected events
    goCue_diff = np.abs(bpod["goCueTrigger_times"] - bpod["goCue_times"])
    errorCue_diff = np.abs(bpod["errorCueTrigger_times"] - bpod["errorCue_times"])
    stimOn_diff = np.abs(bpod["stimOnTrigger_times"] - bpod["stimOn_times"])
    stimOff_diff = np.abs(bpod["stimOffTrigger_times"] - bpod["stimOff_times"])
    stimFreeze_diff = np.abs(bpod["stimFreezeTrigger_times"] - bpod["stimFreeze_times"])

    return {
        "goCue": goCue_diff,
        "errorCue": errorCue_diff,
        "stimOn": stimOn_diff,
        "stimOff": stimOff_diff,
        "stimFreeze": stimFreeze_diff,
    }


def _describe_trigger_diffs(trigger_diffs):
    print(trigger_diffs.describe())
    for k in trigger_diffs:
        print(k, "nancount:", sum(np.isnan(trigger_diffs[k])))

    return trigger_diffs


@uuid_to_path(dl=True)
def describe_sesion_trigger_response_diffs(session_path):
    trigger_diffs = get_session_trigger_response_delays(session_path)
    return _describe_trigger_diffs(trigger_diffs)


def get_trigger_response_diffs(eid_or_path_list):
    trigger_diffs = {
        "goCue": np.array([]),
        "errorCue": np.array([]),
        "stimOn": np.array([]),
        "stimOff": np.array([]),
        "stimFreeze": np.array([]),
    }
    for sess in eid_or_path_list:
        td = get_session_trigger_response_delays(sess)
        for k in trigger_diffs:
            trigger_diffs[k] = np.append(trigger_diffs[k], td[k])

    df = pd.DataFrame.from_dict(trigger_diffs)

    return df


def describe_trigger_response_diffs(eid_or_path_list):
    trigger_diffs = get_trigger_response_diffs(eid_or_path_list)
    return _describe_trigger_diffs(trigger_diffs)


def describe_lab_trigger_response_delays(labname):
    eids, dets = one.search(
        task_protocol="_iblrig_tasks_ephysChoiceWorld6.2.5",
        lab=labname,
        dataset_types=["_iblrig_taskData.raw", "_iblrig_taskSettings.raw"],
        details=True,
    )
    trigger_diffs = get_trigger_response_diffs(eids)
    return _describe_trigger_diffs(trigger_diffs)


if __name__ == "__main__":
    # from ibllib.ephys.bpodqc import *
    subj_path = "/home/nico/Projects/IBL/github/iblapps/scratch/TestSubjects/"
    # Guido's 3B
    gsession_path = subj_path + "_iblrig_test_mouse/2020-02-11/001"
    # Alex's 3A
    asession_path = subj_path + "_iblrig_test_mouse/2020-02-18/006"
    a2session_path = subj_path + "_iblrig_test_mouse/2020-02-21/011"
    eid = "af74b29d-a671-4c22-a5e8-1e3d27e362f3"

    session_path = gsession_path
    # bpod = load_bpod_data(session_path)
    # fpgaqc_frame = _qc_from_path(session_path, display=False)
    # bpodqc_frame = get_bpodqc_frame(session_path)

    # bla = [(
    # k, all(fpgaqc_frame[k] == bpodqc_frame[k])) for k in fpgaqc_frame if k in bpodqc_frame
    # ]

    # count_qc_failures(session_path)
    # plt.ion()
    # f, ax = plt.subplots()
    # plot_bpod_session(session_path, ax=ax)

    # eid = "a71175be-d1fd-47a3-aa93-b830ea3634a1"
    # plot_session_trigger_response_diffs(eid)
    # one.search_terms()
    # eids, dets = one.search(task_protocol="ephysChoiceWorld6.2.5", lab="mainenlab", details=True)
    labs = one.list(None, "lab")
    # for lab in labs:
    #     eids, dets = one.search(
    #         task_protocol="ephysChoiceWorld6.2.5",
    #         lab=lab,
    #         details=True,
    #         dataset_types=["_iblrig_taskData.raw", "_iblrig_taskSettings.raw"],
    #     )
    #     print(lab, len(eids))
    # for eid in eids:
    #     plot_session_trigger_response_diffs(eid)
    lab = "churchlandlab"
    eid = '0deb75fb-9088-42d9-b744-012fb8fc4afb'

    bla1, bla2 = get_bpod_fronts(eid)
    # for lab in labs:
    #     describe_lab_trigger_response_diffs(lab)

print(".")