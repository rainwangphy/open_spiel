# Copyright 2019 DeepMind Technologies Ltd. All rights reserved.
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

# Lint as python3
"""Tests for Python Predator-Prey game."""

import math
from absl.testing import absltest
from absl.testing import parameterized
import numpy as np
import numpy.testing as npt
from open_spiel.python.mfg.games import predator_prey
import pyspiel


class MFGCrowdModellingGameTest(parameterized.TestCase):

  def test_load(self):
    game = pyspiel.load_game('python_mfg_predator_prey')
    game.new_initial_state_for_population(0)
    game.new_initial_state_for_population(1)

  @parameterized.parameters(
      {
          'geometry': predator_prey.Geometry.SQUARE,
          'expected_pos': np.array([0, 4])
      },
      {
          'geometry': predator_prey.Geometry.TORUS,
          'expected_pos': np.array([0, 0])
      },
  )
  def test_dynamics(self, geometry, expected_pos):
    game = pyspiel.load_game('python_mfg_predator_prey', {'geometry': geometry})
    state = game.new_initial_state_for_population(2)
    # Initial chance node.
    self.assertEqual(state.current_player(), pyspiel.PlayerId.CHANCE)
    self.assertLen(state.chance_outcomes(), 1)
    self.assertEqual(state.chance_outcomes()[0][0],
                     predator_prey.pos_to_merged(np.array([0, 4]), state.size))
    state.apply_action(state.chance_outcomes()[0][0])
    self.assertEqual(state.current_player(), 2)
    npt.assert_array_equal(state.pos, [0, 4])
    self.assertEqual(state._action_to_string(player=2, action=2), '[0 1]')
    state.apply_action(2)
    npt.assert_array_equal(state.pos, expected_pos)

  def test_create_with_params(self):
    game = pyspiel.load_game('python_mfg_predator_prey(horizon=100,size=20)')
    self.assertEqual(game.size, 20)
    self.assertEqual(game.horizon, 100)

  def check_cloning(self, state):
    cloned = state.clone()
    self.assertEqual(str(cloned), str(state))
    self.assertEqual(cloned._distribution, state._distribution)
    self.assertEqual(cloned.current_player(), state.current_player())
    self.assertEqual(cloned.size, state.size)
    self.assertEqual(cloned.horizon, state.horizon)

  @parameterized.parameters(
      {'population': 0},
      {'population': 1},
      {'population': 2},
  )
  def test_random_game(self, population):
    """Tests basic API functions."""
    np.random.seed(7)
    horizon = 10
    size = 20
    game = predator_prey.MFGPredatorPreyGame(params={
        'horizon': horizon,
        'size': size,
    })
    state = game.new_initial_state_for_population(population)
    t = 0
    while not state.is_terminal():
      if state.current_player() == pyspiel.PlayerId.CHANCE:
        actions, probs = zip(*state.chance_outcomes())
        action = np.random.choice(actions, p=probs)
        self.check_cloning(state)
        self.assertEqual(
            len(state.legal_actions()), len(state.chance_outcomes()))
        state.apply_action(action)
      elif state.current_player() == pyspiel.PlayerId.MEAN_FIELD:
        self.assertEqual(state.legal_actions(), [])
        self.check_cloning(state)
        num_states = len(state.distribution_support())
        state.update_distribution([1 / num_states] * num_states)
      else:
        self.assertEqual(state.current_player(), population)
        self.check_cloning(state)
        state.observation_string()
        state.information_state_string()
        legal_actions = state.legal_actions()
        action = np.random.choice(legal_actions)
        state.apply_action(action)
        t += 1

    self.assertEqual(t, horizon)

  @parameterized.parameters(
      {
          'reward_matrix':
              np.array([
                  [0, 1],  #
                  [-1, 0]
              ]),
          'population':
              0,
          'initial_pos':
              np.array([0, 0]),
          'distributions': [
              # First pop.
              np.array([
                  [1, 0],  #
                  [0, 0]
              ]),
              # Second pop.
              np.array([
                  [0.5, 0.1],  #
                  [0, 0.9]
              ])
          ],
          'expected_rewards':
              np.array([
                  -math.log(1 + 1e-25) + 0.5,  #
                  -math.log(0.5 + 1e-25) - 1,
              ]),
      },
      {
          'reward_matrix':
              np.array([
                  [0, -1, 0.5],  #
                  [0.5, 0, -1],  #
                  [-0.5, 1, 0],
              ]),
          'population':
              2,
          'initial_pos':
              np.array([1, 1]),
          'distributions': [
              # First pop.
              np.array([
                  [0.1, 0.2],  #
                  [0.3, 0.4]
              ]),
              # Second pop.
              np.array([
                  [0.2, 0.1],  #
                  [0.1, 0.6]
              ]),
              # Third pop.
              np.array([
                  [0, 0.1],  #
                  [0.1, 0.8]
              ]),
          ],
          'expected_rewards':
              np.array([
                  -math.log(0.4 + 1e-25) - 0.6 + 0.5 * 0.8,
                  -math.log(0.6 + 1e-25) + 0.5 * 0.4 - 0.8,
                  -math.log(0.8 + 1e-25) - 0.5 * 0.4 + 0.6,
              ]),
      },
  )
  def test_rewards(self, reward_matrix, population, initial_pos, distributions,
                   expected_rewards):
    game = pyspiel.load_game(
        'python_mfg_predator_prey', {
            'size': 2,
            'reward_matrix': ' '.join(str(v) for v in reward_matrix.flatten())
        })
    state = game.new_initial_state_for_population(population)
    # Initial chance node.
    self.assertEqual(state.current_player(), pyspiel.PlayerId.CHANCE)
    state.apply_action(predator_prey.pos_to_merged(initial_pos, state.size))
    self.assertEqual(state.current_player(), population)
    npt.assert_array_equal(state.pos, initial_pos)
    state.apply_action(state._NEUTRAL_ACTION)
    npt.assert_array_equal(state.pos, initial_pos)
    self.assertEqual(state.current_player(), pyspiel.PlayerId.MEAN_FIELD)

    # Maps states (in string representation) to their proba.
    dist = {}
    for x in range(state.size):
      for y in range(state.size):
        for pop in range(len(reward_matrix)):
          dist[state.state_to_str(
              np.array([x, y]), state.t, pop,
              player_id=pop)] = distributions[pop][y][x]
    support = state.distribution_support()
    state.update_distribution([dist[s] for s in support])

    self.assertEqual(state.current_player(), pyspiel.PlayerId.CHANCE)
    state.apply_action(state._NEUTRAL_ACTION)
    # Decision node where we get a reward.
    self.assertEqual(state.current_player(), population)
    npt.assert_array_equal(state.rewards(), expected_rewards)


if __name__ == '__main__':
  absltest.main()
