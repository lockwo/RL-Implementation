import gym
import numpy as np
import random
import matplotlib.pyplot as plt
import math
import tensorflow as tf
from collections import deque

#tf.compat.v1.disable_eager_execution()
#tf.keras.backend.set_floatx('float64')
class DDPG_AGENT(object):
    def __init__(self, action_size, state_size, batch_size):
        self.action_space = action_size
        self.state_space = state_size
        self.act_range = 2.0
        self.actor_opt = tf.keras.optimizers.Adam(lr=0.001)
        self.critic_opt = tf.keras.optimizers.Adam(lr=0.001)
        self.q1 = self.make_critic()
        self.q2 = self.make_critic()
        self.q1_target = self.make_critic()
        self.q2_target = self.make_critic()
        self.policy = self.make_actor()
        self.policy_target = self.make_actor()
        self.policy_counter = 0
        self.move_weights()
        self.buff = 50000
        self.states = np.zeros((self.buff, self.state_space[0]))
        self.actions = np.zeros((self.buff, self.action_space[0]))
        self.rewards = np.zeros((self.buff, 1))
        self.next_states = np.zeros((self.buff, self.state_space[0]))
        self.counter = 0
        self.batch = batch_size
        self.gamma = 0.99 # DISCOUNT FACTOR, CLOSE TO 1 = LONG TERM
        self.tau = 0.005
        self.policy_delay = 3
        # Noise variables
        self.mean = 0
        self.std = 0.1
     
    def make_critic(self):
        state_ = tf.keras.layers.Input(shape=(self.state_space[0]))
        action_ = tf.keras.layers.Input(shape=(self.action_space[0]))
        state = tf.keras.layers.Dense(32, activation='relu', name='state1')(state_)
        #state = tf.keras.layers.Dense(32, activation='relu', name='state2')(state)
        action = tf.keras.layers.Dense(32, activation='relu', name='act1')(action_)
        x = tf.keras.layers.Concatenate()([state, action])
        x = tf.keras.layers.Dense(256, activation='relu', name='dense2')(x)
        x = tf.keras.layers.Dense(256, activation='relu', name='dense3')(x)
        x = tf.keras.layers.Dense(self.action_space[0], name='output')(x)
        model = tf.keras.models.Model(inputs=[state_, action_], outputs=x)
        model.summary()
        return model
    
    def make_actor(self):
        last_init = tf.random_uniform_initializer(minval=-0.003, maxval=0.003)
        state_ = tf.keras.layers.Input(shape=(self.state_space[0]))
        x = tf.keras.layers.Dense(128, activation='relu', name='dense1')(state_)
        x = tf.keras.layers.Dense(256, activation='relu', name='dense2')(x)
        x = tf.keras.layers.Dense(128, activation='relu', name='dense3')(x)
        x = tf.keras.layers.Dense(self.action_space[0], activation='tanh', name='output', kernel_initializer=last_init)(x)
        x = x * self.act_range
        model = tf.keras.models.Model(inputs=state_, outputs=x)
        model.summary()
        return model

    def remember(self, state, action, reward, next_state, _):
        i = self.counter % self.buff
        self.states[i] = state
        self.actions[i] = action
        self.rewards[i] = reward
        self.next_states[i] = next_state
        self.counter += 1

    def move_weights(self):
        self.q1_target.set_weights(self.q1.get_weights())
        self.q2_target.set_weights(self.q2.get_weights())
        self.policy_target.set_weights(self.policy.get_weights())

    def get_action(self, obs):
        action = tf.squeeze(self.policy(np.array([obs,])))
        act = action.numpy() + np.random.normal(self.mean, self.std, 1)[0]
        act = np.clip(act, -self.act_range, self.act_range)
        return [np.squeeze(act)]

    def train(self):
        batch_indices = np.random.choice(min(self.counter, self.buff), self.batch)
        state_batch = tf.convert_to_tensor(self.states[batch_indices])
        action_batch = tf.convert_to_tensor(self.actions[batch_indices])
        reward_batch = tf.convert_to_tensor(self.rewards[batch_indices])
        reward_batch = tf.cast(reward_batch, dtype=tf.float32)
        next_state_batch = tf.convert_to_tensor(self.next_states[batch_indices])
        # Train critic
        with tf.GradientTape(persistent=True) as tape:
            targets_act = tf.clip_by_value(tf.math.add(self.policy_target(next_state_batch, training=True),  tf.random.normal([self.batch, 1], self.mean, self.std)), -self.act_range, self.act_range)
            bellman = reward_batch + self.gamma * tf.math.minimum(self.q1_target([next_state_batch, targets_act], training=True), self.q2_target([next_state_batch, targets_act], training=True))
            critic1 = self.q1([state_batch, action_batch], training=True)
            critic2 = self.q2([state_batch, action_batch], training=True)
            msbe1 = tf.math.reduce_mean(tf.math.square(bellman - critic1))
            msbe2 = tf.math.reduce_mean(tf.math.square(bellman - critic2))
        
        critic1_gradients = tape.gradient(msbe1, self.q1.trainable_variables)
        self.critic_opt.apply_gradients(zip(critic1_gradients, self.q1.trainable_variables))
        critic2_gradients = tape.gradient(msbe2, self.q2.trainable_variables)
        self.critic_opt.apply_gradients(zip(critic2_gradients, self.q2.trainable_variables))

        self.update_target(self.q1_target.trainable_variables, self.q1.trainable_variables)
        self.update_target(self.q2_target.trainable_variables, self.q2.trainable_variables)

        if self.policy_counter % self.policy_delay == 0:
            with tf.GradientTape() as tape:
                actions = self.policy(state_batch, training=True)
                critic = tf.math.minimum(self.q1([state_batch, actions], training=True), self.q2([state_batch, actions], training=True))
                policy_loss = -tf.math.reduce_mean(critic)
            
            policy_gradients = tape.gradient(policy_loss, self.policy.trainable_variables)
            self.actor_opt.apply_gradients(zip(policy_gradients, self.policy.trainable_variables))


            self.update_target(self.policy_target.trainable_variables, self.policy.trainable_variables)
       
        self.policy_counter += 1
    
    @tf.function
    def update_target(self, target_weights, weights):
        for (a, b) in zip(target_weights, weights):
            a.assign(b * self.tau + a * (1 - self.tau))

# Hyperparameters
ITERATIONS = 120
batch_size = 100
windows = 20
learn_delay = 200

env = gym.make("Pendulum-v0")
'''env.observation_space.shape'''
print(env.action_space, env.action_space.shape)
print(env.observation_space, env.observation_space.shape)
agent = DDPG_AGENT(env.action_space.shape, env.observation_space.shape, batch_size)
rewards = []
avg_reward = deque(maxlen=ITERATIONS)
best_avg_reward = -math.inf
rs = deque(maxlen=windows)

for i in range(ITERATIONS):
    s1 = env.reset()
    total_reward = 0
    done = False
    step = 0
    while not done:
        #env.render()
        action = agent.get_action(s1)
        s2, reward, done, info = env.step(action)
        total_reward += reward
        agent.remember(s1, action, reward, s2, done)
        if agent.counter > learn_delay:
            agent.train()
        if done:
            rewards.append(total_reward)
            rs.append(total_reward)
        else:
            s1 = s2
        step += 1
    if i >= windows:
        avg = np.mean(rs)
        avg_reward.append(avg)
        if avg > best_avg_reward:
            best_avg_reward = avg
            #agent.q_network.save("dqn_cartpole.h5")
    else: 
        avg_reward.append(-2000)
    
    print("\rEpisode {}/{} || Best average reward {}, Current Iteration Reward {}".format(i, ITERATIONS, best_avg_reward, total_reward) , end='', flush=True)

#np.save("rewards", np.asarray(rewards))
#np.save("averages", np.asarray(avg_reward))
#plt.ylim(-2000,1)
plt.plot(rewards, color='olive', label='Reward')
plt.plot(avg_reward, color='red', label='Average')
plt.legend()
plt.title("TD3 On Pendulum")
plt.ylabel('Reward')
plt.xlabel('Generation')
plt.show()
