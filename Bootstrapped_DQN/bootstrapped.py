import gym
import numpy as np
import random
import matplotlib.pyplot as plt
import math
from collections import deque
import tensorflow as tf

tf.compat.v1.disable_eager_execution()

class Bootstrap_dqn(object):
    def __init__(self, action_size, state_size, batch_size):
        self.action_space = action_size
        self.memory = deque(maxlen=20000)
        self.batch = batch_size
        # Q Learning Parameters
        self.gamma = 0.98 # DISCOUNT FACTOR, CLOSE TO 1 = LONG TERM
        self.K = 10 # Number of heads, from paper
        self.q_network = self.make_net(state_size)

    def make_net(self, state):
        inputs = tf.keras.layers.Input(shape=(state))
        x = tf.keras.layers.Dense(32, activation='relu', name='dense1')(inputs)
        x = tf.keras.layers.Dense(64, activation='relu', name='dense2')(x)
        heads = []
        for i in range(self.K):
            l_name1 = "head_"
            l_name1 += str(i)
            o_name = "out_"
            o_name += str(i)
            y = tf.keras.layers.Dense(32, activation='relu', name=l_name1)(x)
            z = tf.keras.layers.Dense(self.action_space, name=o_name)(y)
            model = tf.keras.models.Model(inputs=inputs, outputs=z)
            model.compile(optimizer=tf.keras.optimizers.Adam(), loss='mse')
            heads.append(model)
        
        #model.summary()
        #tf.keras.utils.plot_model(model, to_file='test.png')
        return heads

    def remember(self, state, action, reward, next_state, done, mask):
        self.memory.append((state, action, reward, next_state, done, mask))

    def get_action(self, obs, mask):
        return np.argmax(self.q_network[mask].predict(np.array([obs,]))[0])

    def train(self):
        minibatch = random.sample(self.memory, self.batch)
        for state, action, reward, next_state, done, mask in minibatch:
            state = np.array([state,])
            next_state = np.array([next_state,])
            target_f = self.q_network[mask].predict(state)[0]
            if done:
                target_f[action] = reward
            else:
                q_pred = np.amax(self.q_network[mask].predict(next_state)[0])
                target_f[action] = reward + self.gamma*q_pred
            target_f = np.array([target_f,])
            self.q_network[mask].fit(state, target_f, epochs=1, verbose=0)



# Hyperparameters
ITERATIONS = 1000
batch_size = 128
windows = 50

env = gym.make("CartPole-v1")
'''env.observation_space.shape'''
print(env.action_space)
print(env.observation_space, env.observation_space.shape)
agent = Bootstrap_dqn(env.action_space.n, env.observation_space.shape, batch_size)
rewards = []
# Uncomment the line before to load model
#agent.q_network = tf.keras.models.load_model("cartpole.h5")
avg_reward = deque(maxlen=ITERATIONS)
best_avg_reward = -math.inf
rs = deque(maxlen=windows)

for i in range(ITERATIONS):
    s1 = env.reset()
    total_reward = 0
    done = False
    mask = random.randint(0, agent.K-1)
    while not done:
        #env.render()
        #print(s1)
        action = agent.get_action(s1, mask)
        s2, reward, done, info = env.step(action)
        total_reward += reward
        agent.remember(s1, action, reward, s2, done, mask)
        if len(agent.memory) > 1000 and done:
            agent.train()
        if done:
            rewards.append(total_reward)
            rs.append(total_reward)
        else:
            s1 = s2
    if i >= windows:
        avg = np.mean(rs)
        avg_reward.append(avg)
        if avg > best_avg_reward:
            best_avg_reward = avg
            #agent.q_network.save("dqn_cartpole.h5")
    else: 
        avg_reward.append(8)
    
    print("\rEpisode {}/{} || Best average reward {}, Current Iteration Reward {}".format(i, ITERATIONS, best_avg_reward, total_reward) , end='', flush=True)

#np.save("rewards", np.asarray(rewards))
#np.save("averages", np.asarray(avg_reward))
plt.ylim(0,500)
plt.plot(rewards, color='olive', label='Reward')
plt.plot(avg_reward, color='red', label='Average')
plt.legend()
plt.ylabel('Reward')
plt.xlabel('Generation')
plt.show()
