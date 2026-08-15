"""
The reinforcement-learning stack, which had no tests at all.

`rl/` is 1,917 lines and was carried through the August audit untested, on the
grounds that its *implementation* looked sound. That is not the same as knowing
it. The audit's own finding was that a correct-looking training loop had been
optimising a metric that scored the wrong player for 89 runs, and nothing in
the code said so — only a measurement did.

So these are the invariants a training run silently violates rather than
crashes on:

* the observation the environment hands the network is the one the engine
  defines, and stays that size,
* chips are conserved through an episode,
* an illegal action requested by the network never reaches the engine,
* an episode ends,
* and one PPO update runs without producing NaN.

The last matters most. A NaN in the policy does not raise; it makes every
subsequent action uniform, and the run continues to completion looking merely
disappointing.

    python -m pytest tests/test_rl.py -q
"""
import numpy as np
import pytest

from engine import get_abstract_action_mask, get_feature_names
from rl import PokerEnv, PPOAgent, PPOConfig, PPOTrainer

TOTAL_CHIPS = 2 * 200


@pytest.fixture
def env():
    return PokerEnv(num_players=2, starting_stack=200, small_blind=1,
                    big_blind=2, seed=7)


@pytest.fixture
def config(tmp_path):
    """A trainer small enough to run one real update inside a test."""
    return PPOConfig(num_players=2, starting_stack=200, small_blind=1,
                     big_blind=2, n_steps=24, batch_size=8, n_epochs=1,
                     hidden_size=16, num_layers=1, total_hands=24,
                     eval_every=10 ** 9, save_every=10 ** 9,
                     device="cpu", seed=0, checkpoint_dir=str(tmp_path),
                     log_dir=str(tmp_path), verbose=False)


# ---------------------------------------------------------------------------
# The observation contract
# ---------------------------------------------------------------------------

def test_the_environment_and_the_engine_agree_on_the_observation_size():
    """
    `PokerEnv.OBS_SIZE` and `PPOConfig.obs_size` are both hardcoded, and the
    engine defines the layout separately. If they drift, the network is fed a
    truncated or padded vector and trains happily on it — which is the exact
    shape of the bug the audit found between `FeatureCache` and
    `get_state_vector`.

    This will fail the moment the feature layer is rebuilt, which is the point:
    it names every place that has to move together.
    """
    engine_features = len(get_feature_names())
    assert PokerEnv.OBS_SIZE == engine_features, (
        f"env expects {PokerEnv.OBS_SIZE} features, engine defines "
        f"{engine_features}")
    assert PPOConfig().obs_size == engine_features, (
        f"PPO config expects {PPOConfig().obs_size}, engine defines "
        f"{engine_features}")


def test_reset_and_step_return_the_declared_shape(env):
    obs, info = env.reset()
    assert obs.shape == (PokerEnv.OBS_SIZE,), obs.shape
    assert obs.dtype == np.float32, obs.dtype
    assert "game_seed" in info

    obs, _reward, _terminated, truncated, _info = env.step(1)
    assert obs.shape == (PokerEnv.OBS_SIZE,), obs.shape
    assert obs.dtype == np.float32, obs.dtype
    assert truncated is False, "the env declares no time-limit truncation"


def test_observations_stay_inside_the_declared_box(env):
    """
    The env advertises a Box(0, 1) observation space. A feature outside it is
    not fatal, but it silently breaks any normalisation assumption downstream —
    and the space is what a reader trusts.
    """
    rng = np.random.default_rng(0)
    obs, _ = env.reset()
    seen = [obs]

    for _ in range(200):
        obs, _r, terminated, _t, _i = env.step(int(rng.integers(6)))
        seen.append(obs)
        if terminated:
            obs, _ = env.reset()
            seen.append(obs)

    stacked = np.array(seen)
    assert np.isfinite(stacked).all(), "non-finite feature reached the network"
    # BoxSpace stores the bounds as arrays broadcast to the observation shape.
    floor = float(np.min(env.observation_space.low))
    ceiling = float(np.max(env.observation_space.high))
    offenders = [
        (name, float(stacked[:, i].min()), float(stacked[:, i].max()))
        for i, name in enumerate(get_feature_names())
        if stacked[:, i].min() < floor - 1e-6 or stacked[:, i].max() > ceiling + 1e-6
    ]
    assert not offenders, (
        f"features outside the declared Box({floor}, {ceiling}): {offenders}")


# ---------------------------------------------------------------------------
# What the environment must never do
# ---------------------------------------------------------------------------

def test_an_illegal_action_never_reaches_the_engine(env):
    """
    The network emits an index over all six abstract actions regardless of
    which are legal. The env masks and substitutes. If that substitution were
    wrong the engine would raise — but the audit found the previous training
    loop catching such failures and converting them to folds, so an agent
    emitting illegal actions every hand scored as merely weak.
    """
    rng = np.random.default_rng(1)
    env.reset()

    for _ in range(400):
        # Deliberately unfiltered: ask for whatever, legal or not.
        _obs, _r, terminated, _t, _i = env.step(int(rng.integers(6)))
        if terminated:
            env.reset()


def test_chips_are_conserved_across_an_episode(env):
    """Two hundred chips each in, four hundred out, every hand."""
    rng = np.random.default_rng(2)

    for _ in range(20):
        env.reset()
        terminated = False
        guard = 0
        while not terminated and guard < 200:
            _obs, _r, terminated, _t, _i = env.step(int(rng.integers(6)))
            guard += 1
        assert guard < 200, "episode did not terminate"

        game = env._game
        total = sum(p.stack for p in game.players) + game.state.pot.total
        assert total == TOTAL_CHIPS, f"chips became {total}"


def test_episodes_terminate_and_report_a_consistent_delta(env):
    """
    `chip_delta` and `bb_per_100` describe the same outcome and must agree,
    since downstream reporting picks whichever is convenient.
    """
    rng = np.random.default_rng(3)
    env.reset()

    for _ in range(400):
        _obs, _r, terminated, _t, info = env.step(int(rng.integers(6)))
        if terminated:
            assert "chip_delta" in info and "bb_per_100" in info
            expected = (info["chip_delta"] / env.big_blind) * 100
            assert info["bb_per_100"] == pytest.approx(expected)
            env.reset()


# ---------------------------------------------------------------------------
# The agent and one real update
# ---------------------------------------------------------------------------

def test_the_agent_only_ever_names_a_legal_action(env, config):
    """
    `act` takes the legality mask, so the agent is responsible for respecting
    it — the env's substitution is a backstop, not the mechanism. Asserting the
    action is merely *in range* would pass on an agent that names an illegal
    action every hand and leans on the backstop, which is how the audit found
    the previous loop scoring broken agents as weak ones.
    """
    agent = PPOAgent(config)
    obs, _ = env.reset()

    for _ in range(80):
        mask = np.asarray(get_abstract_action_mask(env._game, env._agent_id))
        action = agent.act(obs, mask)
        index = int(action[0] if isinstance(action, tuple) else action)

        assert 0 <= index < PokerEnv.NUM_ACTIONS, index
        assert mask[index], (
            f"agent chose action {index}, which the mask {mask.tolist()} "
            f"marks illegal")

        obs, _r, terminated, _t, _i = env.step(index)
        if terminated:
            obs, _ = env.reset()


def test_one_ppo_update_produces_no_nan(config):
    """
    The failure this exists for is silent. A NaN in the policy does not raise —
    it makes the action distribution uniform and the run continues to
    completion, looking merely disappointing rather than broken.
    """
    import torch

    trainer = PPOTrainer(config)
    agent = trainer.train()

    parameters = list(agent.net.parameters())
    assert parameters, "agent exposes no parameters"
    for tensor in parameters:
        assert torch.isfinite(tensor).all(), "non-finite parameter after one update"


def test_a_saved_agent_reloads_to_the_same_policy(config, tmp_path):
    """
    Checkpoints are how a run's result survives the run. An agent that reloads
    to a different policy makes every downstream evaluation describe something
    that was never trained.
    """
    agent = PPOAgent(config)
    path = str(tmp_path / "agent.pt")
    agent.save(path)

    revived = PPOAgent.from_checkpoint(path, device="cpu")
    probe = np.zeros(PokerEnv.OBS_SIZE, dtype=np.float32)

    original = agent.get_value(probe)
    reloaded = revived.get_value(probe)
    assert reloaded == pytest.approx(original, abs=1e-6), (original, reloaded)
