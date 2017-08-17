import tensorflow as tf
import numpy as np

# Flatten gradient along all variables
def flatgrad(loss, vrbs):
	# tf.gradients returns list of gradients w.r.t variables
	'''
		If 'loss' argument is list, tf.gradients returns sum of gradient of each loss element for each variables
		tf.gradients([y,z]) => [dy/dx+dz/dx]
	'''
	grads = tf.gradients(loss, vrbs)
	return tf.concat(0, [tf.reshape(g, (np.prod(v.get_shape().as_list()))) for (g, v) in zip(grads, vrbs)])


# mu1, logstd1 : [batch size, action size]
def LOG_POLICY(mu, logstd, action):
	# logstd : log(standard_deviation)
	# variance : exponential(2*log(std))
	variance = tf.exp(2*logstd)
	# Take log to gaussian formula
	log_prob = tf.square(action - mu) / (2*variance) - 0.5*tf.log(2*np.pi) - logstd
	# Make [batch size, ] sum along 'action size' axis
	return tf.reduce_sum(log_prob, 1)


# All argument : [batch size, action size]
# KL divergence between parameterized Gaussian
'''
	P ~ N(mu1, sig1), Q ~ N(mu2, sig2)
	KL(p,q) = log(sig2/sig1) + (sig1**2 + (mu1-mu2)**2)/2(sig2**2) - 0.5
	Referenced at : https://stats.stackexchange.com/questions/7440/kl-divergence-between-two-univariate-gaussian
'''
def GAUSS_KL(mu1, logstd1, mu2, logstd2):
	variance1 = tf.exp(2*logstd1)
	variance2 = tf.exp(2*logstd2)

	kl = logstd2 - logstd1 + (variance1 + tf.square(mu1 - mu2))/(2*variance2)) - 0.5
	return tf.reduce_sum(kl)
	
'''
	Entropy of Gaussian : Expectation[-log(p(x))]
	integral[p(x) *(-logp(x))] : (1+log(2pi(sig**2)))/2
'''
def GAUSS_ENTROPY(mu, logstd):
	variance = tf.exp(2*logstd)
	
	entropy = (1 + tf.log(2*np.pi*variance))/2
	return tf.reduce_sum(entropy)

def GAUSS_KL_FIRST_FIX(mu, logstd):
	# First argument is old policy, so keep it unchanged through tf.stop_gradient 
	mu1, logstd1 = map(tf.stop_gradient, [mu, logstd])
	mu1, logstd2 = mu, logstd
	return GAUSS_KL(mu1, logstd1, mu2, logstd2)

'''
	Conjugate gradient : used to calculate search direction
	Find basis which satisfies <u,v>=u.transpose*Q*v = 0(Q-orthogonal and hessian of objective function)
	Numerical solving Qx=b, Here Q is FIM => solving Ax=-g
'''
def CONJUGATE_GRADIENT(fvp, y, k=10, tolerance=1e-8):
	# Given intial guess, r0 := y-fvp(x0), but our initial value is x0 := 0 so r0 := y
	p = y.copy()
	r = y.copy()	
	x = np.zeros_like(y)
	r_transpose_r = r.dot(r)
	for i in xrange(k):
		FIM_p = fvp(p)
		# alpha := r.t*r/p.t*A*p
		alpha_k = r_transpose_r / p.dot(FIM_p)
		#x_k+1 := x_k + alpha_k*p
		x += alpha_k*p
		#r_k+1 := r_k - alpha_k*A*p
		r -= alpha_k*FIM_p
		# beta_k = r_k+1.t*r_k+1/r_k.t*r_k
		new_r_transpose_r = r.dot(r)
		beta_k = new_r_transpose_r / r_transpose_r
		# p_k+1 := r_k+1 + beta_k*p_k
		p = r + beta_k*p
		r_transpose_r = new_r_tranpose_r
		if r_transpose_r < tolerance:
			break
	return x



def LINE_SEARCH(surr, theta_prev, full_step, num_backtracking=10):
	prev_sur_objective = surr(theta_prev)
	# backtracking :1,1/2,1/4,1/8...
	for num_bt, fraction in enumerate(0.5**np.arange(num_backtraking)):
		# Exponentially shrink beta
		step_frac = full_step*fraction
		# theta -> theta + step
		theta_new = theta_prev + step_frac
		new_sur_objective = surr(theta_new)
		sur_improvement = new_sur_objective - prev_sur_objective
		if sur_improvement > 0:
			print('Objective improved')
			return theta_new
	print('Objective not improved')	
	return theta_prev
			


# Get actual value
class GetValue:
	def __init__(self, sess, variable_list):
		self.sess = sess
		self.op_list = [tf.reshape(v, (np.prod(v.get_shape().as_list()))) for v in variable_list]

	# Use class instance as function
	def __call__(self):
		return self.op_list.eval(session=self.sess)

# Set parameter value
class SetValue:
	def __init__(self, sess, variable_list):
		self.sess = sess
		shape_list = list()
		for i in variable_list:
			shape_list.append(i.get_shape().as_list())
		total_variable_size = np.sum(np.prod(shapes) for shapes in shape_list)
		self.var_list = tf.placeholder(tf.float32, [total_variable_size])
		start = 0
		assign_ops = list()
		for (shape, var) in zip(shape_list, variable_list):
			variable_size = np.prod(shape)
			assign_ops.append(tf.assign(var, tf.reshape(self.var_list[start:(start+variable_size)], shape)))
			start += size
		# Need '*' to represenet list
		self.op_list = tf.group(*assign_ops)
			
	def __call__(self, var):
		self.sess.run(self.op_list, feed_dict={self.var_list:var})






